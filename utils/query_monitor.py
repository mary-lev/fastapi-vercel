"""
Database Query Performance Monitoring
Provides tools for monitoring slow queries, connection usage, and database performance
"""

import time
import functools
from typing import Optional, Dict, Any, List
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading

from utils.structured_logging import get_logger, LogCategory

logger = get_logger("query_monitor")

# ============================================================================
# QUERY PERFORMANCE TRACKING
# ============================================================================


@dataclass
class QueryMetrics:
    """Stores metrics for database queries"""

    query_hash: str
    sql_statement: str
    parameters: Optional[Dict] = None
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    connection_info: Optional[Dict] = None
    is_slow: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_hash": self.query_hash,
            "sql_preview": self.sql_statement[:100] + "..." if len(self.sql_statement) > 100 else self.sql_statement,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "is_slow": self.is_slow,
            "parameter_count": len(self.parameters) if self.parameters else 0,
        }


class QueryMonitor:
    """Monitor and track database query performance"""

    def __init__(self, slow_query_threshold_ms: float = 1000.0):
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.query_metrics: List[QueryMetrics] = []
        self.slow_queries: List[QueryMetrics] = []
        self.query_counts: Dict[str, int] = {}
        self.total_queries = 0
        self.total_duration_ms = 0.0
        self._lock = threading.Lock()

        # Statistics tracking
        self.stats = {
            "queries_per_minute": [],
            "average_duration_ms": 0.0,
            "slowest_query_ms": 0.0,
            "connection_pool_stats": {},
        }

    def record_query(self, metrics: QueryMetrics):
        """Record a query execution"""
        with self._lock:
            # Generate query hash for grouping similar queries
            query_hash = self._generate_query_hash(metrics.sql_statement)
            metrics.query_hash = query_hash

            # Check if it's a slow query
            if metrics.duration_ms > self.slow_query_threshold_ms:
                metrics.is_slow = True
                self.slow_queries.append(metrics)

                # Log slow query
                logger.warning(
                    f"Slow query detected: {metrics.duration_ms:.2f}ms",
                    category=LogCategory.PERFORMANCE,
                    duration_ms=metrics.duration_ms,
                    extra={
                        "sql_preview": metrics.sql_statement[:200],
                        "query_hash": query_hash,
                        "threshold_ms": self.slow_query_threshold_ms,
                    },
                )

            # Update statistics
            self.query_metrics.append(metrics)
            self.query_counts[query_hash] = self.query_counts.get(query_hash, 0) + 1
            self.total_queries += 1
            self.total_duration_ms += metrics.duration_ms

            # Update average duration
            self.stats["average_duration_ms"] = self.total_duration_ms / self.total_queries

            # Update slowest query
            if metrics.duration_ms > self.stats["slowest_query_ms"]:
                self.stats["slowest_query_ms"] = metrics.duration_ms

            # Cleanup old metrics (keep last 1000 queries)
            if len(self.query_metrics) > 1000:
                self.query_metrics = self.query_metrics[-1000:]

            # Keep only last 100 slow queries
            if len(self.slow_queries) > 100:
                self.slow_queries = self.slow_queries[-100:]

    def _generate_query_hash(self, sql: str) -> str:
        """Generate a hash for similar queries (normalize parameters)"""
        import hashlib
        import re

        # Normalize SQL by removing parameters and extra whitespace
        normalized = re.sub(r"\b\d+\b", "?", sql)  # Replace numbers with ?
        normalized = re.sub(r"'[^']*'", "'?'", normalized)  # Replace string literals
        normalized = re.sub(r"\s+", " ", normalized.strip())  # Normalize whitespace

        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent slow queries"""
        with self._lock:
            return [q.to_dict() for q in sorted(self.slow_queries, key=lambda x: x.duration_ms, reverse=True)[:limit]]

    def get_query_statistics(self) -> Dict[str, Any]:
        """Get comprehensive query statistics"""
        with self._lock:
            recent_queries = self.query_metrics[-100:] if self.query_metrics else []

            # Calculate queries per minute for last hour
            now = datetime.utcnow()
            recent_count = len([q for q in recent_queries if now - q.timestamp < timedelta(minutes=1)])

            # Most frequent queries
            top_queries = sorted(self.query_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            return {
                "total_queries": self.total_queries,
                "queries_per_minute": recent_count,
                "average_duration_ms": round(self.stats["average_duration_ms"], 2),
                "slowest_query_ms": round(self.stats["slowest_query_ms"], 2),
                "slow_query_count": len(self.slow_queries),
                "slow_query_threshold_ms": self.slow_query_threshold_ms,
                "top_query_patterns": [{"hash": hash_val, "count": count} for hash_val, count in top_queries],
                "recent_queries_count": len(recent_queries),
            }


# Global monitor instance
query_monitor = QueryMonitor()

# ============================================================================
# SQLALCHEMY EVENT LISTENERS
# ============================================================================


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Record query start time"""
    context._query_start_time = time.time()
    context._query_statement = statement
    context._query_parameters = parameters


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Record query completion and metrics"""
    if hasattr(context, "_query_start_time"):
        duration_ms = (time.time() - context._query_start_time) * 1000

        metrics = QueryMetrics(
            query_hash="",  # Will be set by monitor
            sql_statement=statement,
            parameters=parameters,
            duration_ms=duration_ms,
            connection_info={"connection_id": id(conn), "executemany": executemany},
        )

        query_monitor.record_query(metrics)


# ============================================================================
# DECORATORS AND CONTEXT MANAGERS
# ============================================================================


def monitor_query_performance(threshold_ms: float = 1000.0):
    """Decorator to monitor query performance in functions"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                if duration_ms > threshold_ms:
                    logger.warning(
                        f"Slow database operation in {func.__name__}: {duration_ms:.2f}ms",
                        category=LogCategory.PERFORMANCE,
                        function=func.__name__,
                        duration_ms=duration_ms,
                        threshold_ms=threshold_ms,
                    )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Database operation failed in {func.__name__}: {str(e)}",
                    category=LogCategory.ERROR,
                    function=func.__name__,
                    duration_ms=duration_ms,
                    exception=e,
                )
                raise

        return wrapper

    return decorator


@contextmanager
def query_performance_context(operation_name: str, threshold_ms: float = 1000.0):
    """Context manager for monitoring query performance"""
    start_time = time.time()

    try:
        yield
        duration_ms = (time.time() - start_time) * 1000

        if duration_ms > threshold_ms:
            logger.warning(
                f"Slow database operation '{operation_name}': {duration_ms:.2f}ms",
                category=LogCategory.PERFORMANCE,
                operation=operation_name,
                duration_ms=duration_ms,
            )
        else:
            logger.debug(
                f"Database operation '{operation_name}': {duration_ms:.2f}ms",
                category=LogCategory.PERFORMANCE,
                operation=operation_name,
                duration_ms=duration_ms,
            )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Database operation '{operation_name}' failed: {str(e)}",
            category=LogCategory.ERROR,
            operation=operation_name,
            duration_ms=duration_ms,
            exception=e,
        )
        raise


# ============================================================================
# CONNECTION POOL MONITORING
# ============================================================================


class ConnectionPoolMonitor:
    """Monitor database connection pool health"""

    def __init__(self):
        self.pool_stats = {}
        self.connection_counts = []
        self.last_check = datetime.utcnow()

    def update_pool_stats(self, engine):
        """Update connection pool statistics"""
        if hasattr(engine, "pool"):
            pool = engine.pool
            # Get invalidated count safely
            try:
                invalidated = pool.invalidated()
            except (AttributeError, TypeError):
                try:
                    invalidated = len(pool._invalidated)
                except AttributeError:
                    invalidated = 0

            stats = {
                "size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalidated": invalidated,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Calculate utilization percentage
            total_connections = stats["size"] + stats["overflow"]
            if total_connections > 0:
                stats["utilization_percent"] = (stats["checked_out"] / total_connections) * 100
            else:
                stats["utilization_percent"] = 0

            self.pool_stats = stats

            # Log high utilization
            # if stats["utilization_percent"] > 80:
            #     logger.warning(
            #         f"High connection pool utilization: {stats['utilization_percent']:.1f}%",
            #         category=LogCategory.PERFORMANCE,
            #         extra=stats,
            #     )

    def get_pool_health(self) -> Dict[str, Any]:
        """Get connection pool health status"""
        return {
            "current_stats": self.pool_stats,
            "health_status": self._assess_pool_health(),
            "recommendations": self._get_recommendations(),
        }

    def _assess_pool_health(self) -> str:
        """Assess overall pool health"""
        if not self.pool_stats:
            return "unknown"

        utilization = self.pool_stats.get("utilization_percent", 0)

        if utilization > 90:
            return "critical"
        elif utilization > 75:
            return "warning"
        elif utilization > 50:
            return "good"
        else:
            return "excellent"

    def _get_recommendations(self) -> List[str]:
        """Get optimization recommendations based on pool stats"""
        recommendations = []

        if not self.pool_stats:
            return ["Unable to assess - no pool statistics available"]

        utilization = self.pool_stats.get("utilization_percent", 0)
        overflow = self.pool_stats.get("overflow", 0)

        if utilization > 80:
            recommendations.append("Consider increasing pool_size")

        if overflow > 10:
            recommendations.append("Consider increasing max_overflow")

        if utilization < 20:
            recommendations.append("Pool might be oversized for current load")

        return recommendations or ["Pool configuration appears optimal"]


# Global pool monitor
pool_monitor = ConnectionPoolMonitor()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def get_database_performance_report() -> Dict[str, Any]:
    """Get comprehensive database performance report"""
    return {
        "query_performance": query_monitor.get_query_statistics(),
        "slow_queries": query_monitor.get_slow_queries(),
        "connection_pool": pool_monitor.get_pool_health(),
        "monitoring_config": {
            "slow_query_threshold_ms": query_monitor.slow_query_threshold_ms,
            "monitoring_active": True,
        },
    }


def reset_monitoring_stats():
    """Reset all monitoring statistics (useful for testing)"""
    global query_monitor, pool_monitor
    query_monitor = QueryMonitor()
    pool_monitor = ConnectionPoolMonitor()
    logger.info("Database monitoring statistics reset", category=LogCategory.SYSTEM)
