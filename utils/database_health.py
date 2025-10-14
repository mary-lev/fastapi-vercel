"""
Database Health Monitoring and Diagnostics
Provides comprehensive health checks and diagnostic tools for database monitoring
"""

import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import text, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from dataclasses import dataclass

from db import engine, SessionLocal
from models import Course, Lesson, Topic, Task, User, TaskAttempt, TaskSolution
from utils.structured_logging import get_logger, LogCategory
from utils.query_monitor import get_database_performance_report

logger = get_logger("database_health")

# ============================================================================
# HEALTH CHECK DATA STRUCTURES
# ============================================================================


@dataclass
class HealthCheckResult:
    """Result of a health check operation"""

    name: str
    status: str  # "healthy", "warning", "critical", "unknown"
    duration_ms: float
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2),
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class DatabaseHealthReport:
    """Comprehensive database health report"""

    overall_status: str
    timestamp: datetime
    checks: List[HealthCheckResult]
    performance_summary: Dict[str, Any]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "total_checks": len(self.checks),
                "healthy_checks": len([c for c in self.checks if c.status == "healthy"]),
                "warning_checks": len([c for c in self.checks if c.status == "warning"]),
                "critical_checks": len([c for c in self.checks if c.status == "critical"]),
            },
            "checks": [check.to_dict() for check in self.checks],
            "performance_summary": self.performance_summary,
            "recommendations": self.recommendations,
        }


# ============================================================================
# INDIVIDUAL HEALTH CHECKS
# ============================================================================


def check_database_connectivity() -> HealthCheckResult:
    """Test basic database connectivity"""
    start_time = time.time()

    try:
        with SessionLocal() as db:
            # Simple query to test connectivity
            result = db.execute(text("SELECT 1 as test")).fetchone()

            duration_ms = (time.time() - start_time) * 1000

            if result and result.test == 1:
                return HealthCheckResult(
                    name="database_connectivity",
                    status="healthy",
                    duration_ms=duration_ms,
                    message="Database connection successful",
                    details={"query_result": result.test},
                )
            else:
                return HealthCheckResult(
                    name="database_connectivity",
                    status="critical",
                    duration_ms=duration_ms,
                    message="Database query returned unexpected result",
                )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"Database connectivity check failed: {e}", category=LogCategory.ERROR)

        return HealthCheckResult(
            name="database_connectivity",
            status="critical",
            duration_ms=duration_ms,
            message=f"Database connection failed: {str(e)}",
            details={"error_type": type(e).__name__},
        )


def check_connection_pool_health() -> HealthCheckResult:
    """Check connection pool status and utilization"""
    start_time = time.time()

    try:
        pool = engine.pool
        pool_size = pool.size()
        checked_out = pool.checkedout()
        overflow = pool.overflow()
        # Note: invalidated is a property, not a method in some SQLAlchemy versions
        try:
            invalidated = pool.invalidated()
        except (AttributeError, TypeError):
            try:
                invalidated = len(pool._invalidated)
            except AttributeError:
                invalidated = 0

        duration_ms = (time.time() - start_time) * 1000

        # Calculate utilization (overflow can be negative, so use max(0, overflow))
        total_connections = pool_size + max(0, overflow)
        utilization = (checked_out / total_connections * 100) if total_connections > 0 else 0

        # Determine status based on utilization
        if utilization > 90:
            status = "critical"
            message = f"Connection pool critically high utilization: {utilization:.1f}%"
        elif utilization > 75:
            status = "warning"
            message = f"Connection pool high utilization: {utilization:.1f}%"
        else:
            status = "healthy"
            message = f"Connection pool healthy utilization: {utilization:.1f}%"

        return HealthCheckResult(
            name="connection_pool",
            status=status,
            duration_ms=duration_ms,
            message=message,
            details={
                "pool_size": pool_size,
                "checked_out": checked_out,
                "overflow": overflow,
                "invalidated": invalidated,
                "utilization_percent": round(utilization, 1),
            },
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"Connection pool health check failed: {e}", category=LogCategory.ERROR)

        return HealthCheckResult(
            name="connection_pool",
            status="unknown",
            duration_ms=duration_ms,
            message=f"Unable to check connection pool: {str(e)}",
        )


def check_query_performance() -> HealthCheckResult:
    """Check recent query performance metrics"""
    start_time = time.time()

    try:
        # Get performance report from query monitor
        perf_report = get_database_performance_report()
        query_stats = perf_report.get("query_performance", {})

        duration_ms = (time.time() - start_time) * 1000

        avg_duration = query_stats.get("average_duration_ms", 0)
        slow_query_count = query_stats.get("slow_query_count", 0)
        queries_per_minute = query_stats.get("queries_per_minute", 0)

        # Determine status based on performance metrics
        if avg_duration > 1000 or slow_query_count > 10:
            status = "warning"
            message = f"Performance concerns: {avg_duration:.1f}ms avg, {slow_query_count} slow queries"
        elif avg_duration > 500 or slow_query_count > 5:
            status = "warning"
            message = f"Moderate performance: {avg_duration:.1f}ms avg, {slow_query_count} slow queries"
        else:
            status = "healthy"
            message = f"Good performance: {avg_duration:.1f}ms avg, {slow_query_count} slow queries"

        return HealthCheckResult(
            name="query_performance",
            status=status,
            duration_ms=duration_ms,
            message=message,
            details={
                "average_duration_ms": avg_duration,
                "slow_query_count": slow_query_count,
                "queries_per_minute": queries_per_minute,
                "total_queries": query_stats.get("total_queries", 0),
            },
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"Query performance check failed: {e}", category=LogCategory.ERROR)

        return HealthCheckResult(
            name="query_performance",
            status="unknown",
            duration_ms=duration_ms,
            message=f"Unable to check query performance: {str(e)}",
        )


def check_table_statistics() -> HealthCheckResult:
    """Check basic table statistics and data integrity"""
    start_time = time.time()

    try:
        with SessionLocal() as db:
            # Get basic table counts
            stats = {}

            # Count main entities
            stats["courses"] = db.query(func.count(Course.id)).scalar()
            stats["lessons"] = db.query(func.count(Lesson.id)).scalar()
            stats["topics"] = db.query(func.count(Topic.id)).scalar()
            stats["tasks"] = db.query(func.count(Task.id)).scalar()
            stats["users"] = db.query(func.count(User.id)).scalar()
            stats["task_attempts"] = db.query(func.count(TaskAttempt.id)).scalar()
            stats["task_solutions"] = db.query(func.count(TaskSolution.id)).scalar()

            duration_ms = (time.time() - start_time) * 1000

            # Check for data consistency issues
            issues = []

            # Check if we have courses but no lessons
            if stats["courses"] > 0 and stats["lessons"] == 0:
                issues.append("Courses exist but no lessons found")

            # Check if we have tasks but no attempts
            if stats["tasks"] > 0 and stats["task_attempts"] == 0:
                issues.append("Tasks exist but no attempts found")

            # Determine status
            if issues:
                status = "warning"
                message = f"Data inconsistencies detected: {', '.join(issues)}"
            else:
                status = "healthy"
                message = "Table statistics look healthy"

            return HealthCheckResult(
                name="table_statistics",
                status=status,
                duration_ms=duration_ms,
                message=message,
                details={"table_counts": stats, "issues": issues},
            )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"Table statistics check failed: {e}", category=LogCategory.ERROR)

        return HealthCheckResult(
            name="table_statistics",
            status="critical",
            duration_ms=duration_ms,
            message=f"Unable to check table statistics: {str(e)}",
        )


def check_database_locks() -> HealthCheckResult:
    """Check for database locks and blocking queries"""
    start_time = time.time()

    try:
        with SessionLocal() as db:
            # PostgreSQL-specific query to check for locks
            lock_query = text(
                """
                SELECT 
                    count(*) as total_locks,
                    count(*) FILTER (WHERE granted = false) as waiting_locks,
                    count(*) FILTER (WHERE mode LIKE '%ExclusiveLock%') as exclusive_locks
                FROM pg_locks 
                WHERE relation IS NOT NULL
            """
            )

            result = db.execute(lock_query).fetchone()
            duration_ms = (time.time() - start_time) * 1000

            if result:
                total_locks = result.total_locks
                waiting_locks = result.waiting_locks
                exclusive_locks = result.exclusive_locks

                # Determine status based on lock counts
                if waiting_locks > 5 or exclusive_locks > 10:
                    status = "warning"
                    message = f"High lock activity: {waiting_locks} waiting, {exclusive_locks} exclusive"
                elif waiting_locks > 0:
                    status = "warning"
                    message = f"Some lock contention: {waiting_locks} waiting locks"
                else:
                    status = "healthy"
                    message = f"Minimal lock activity: {total_locks} total locks"

                return HealthCheckResult(
                    name="database_locks",
                    status=status,
                    duration_ms=duration_ms,
                    message=message,
                    details={
                        "total_locks": total_locks,
                        "waiting_locks": waiting_locks,
                        "exclusive_locks": exclusive_locks,
                    },
                )
            else:
                return HealthCheckResult(
                    name="database_locks",
                    status="unknown",
                    duration_ms=duration_ms,
                    message="Unable to retrieve lock information",
                )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"Database locks check skipped (likely not PostgreSQL): {e}", category=LogCategory.DATABASE)

        return HealthCheckResult(
            name="database_locks",
            status="healthy",
            duration_ms=duration_ms,
            message="Lock checking not available for this database type",
        )


def check_index_usage() -> HealthCheckResult:
    """Check if indexes are being used effectively"""
    start_time = time.time()

    try:
        with SessionLocal() as db:
            # PostgreSQL-specific query for index usage
            index_query = text(
                """
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE idx_tup_read > 0
                ORDER BY idx_tup_read DESC
                LIMIT 10
            """
            )

            result = db.execute(index_query).fetchall()
            duration_ms = (time.time() - start_time) * 1000

            if result:
                index_stats = [
                    {
                        "table": row.tablename,
                        "index": row.indexname,
                        "reads": row.idx_tup_read,
                        "fetches": row.idx_tup_fetch,
                    }
                    for row in result
                ]

                total_reads = sum(row.idx_tup_read for row in result)

                if total_reads > 1000:
                    status = "healthy"
                    message = f"Indexes being used effectively: {total_reads} total reads"
                elif total_reads > 100:
                    status = "healthy"
                    message = f"Moderate index usage: {total_reads} total reads"
                else:
                    status = "warning"
                    message = f"Low index usage: {total_reads} total reads"

                return HealthCheckResult(
                    name="index_usage",
                    status=status,
                    duration_ms=duration_ms,
                    message=message,
                    details={"total_index_reads": total_reads, "top_indexes": index_stats},
                )
            else:
                return HealthCheckResult(
                    name="index_usage",
                    status="healthy",
                    duration_ms=duration_ms,
                    message="No index usage data available (possible new database)",
                )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"Index usage check skipped: {e}", category=LogCategory.DATABASE)

        return HealthCheckResult(
            name="index_usage",
            status="healthy",
            duration_ms=duration_ms,
            message="Index usage checking not available for this database type",
        )


# ============================================================================
# COMPREHENSIVE HEALTH CHECK
# ============================================================================


def run_comprehensive_health_check() -> DatabaseHealthReport:
    """Run all health checks and generate comprehensive report"""
    start_time = time.time()

    logger.info("Starting comprehensive database health check", category=LogCategory.DATABASE)

    # Run all health checks
    checks = [
        check_database_connectivity(),
        check_connection_pool_health(),
        check_query_performance(),
        check_table_statistics(),
        check_database_locks(),
        check_index_usage(),
    ]

    # Determine overall status
    critical_checks = [c for c in checks if c.status == "critical"]
    warning_checks = [c for c in checks if c.status == "warning"]

    if critical_checks:
        overall_status = "critical"
    elif warning_checks:
        overall_status = "warning"
    else:
        overall_status = "healthy"

    # Get performance summary
    try:
        performance_summary = get_database_performance_report()
    except Exception as e:
        logger.warning(f"Failed to get performance summary: {e}", category=LogCategory.DATABASE)
        performance_summary = {"error": "Performance data unavailable"}

    # Generate recommendations
    recommendations = _generate_recommendations(checks, performance_summary)

    report = DatabaseHealthReport(
        overall_status=overall_status,
        timestamp=datetime.utcnow(),
        checks=checks,
        performance_summary=performance_summary,
        recommendations=recommendations,
    )

    duration_ms = (time.time() - start_time) * 1000

    logger.info(
        f"Database health check completed in {duration_ms:.2f}ms",
        category=LogCategory.DATABASE,
        overall_status=overall_status,
        total_checks=len(checks),
        critical_checks=len(critical_checks),
        warning_checks=len(warning_checks),
    )

    return report


def _generate_recommendations(checks: List[HealthCheckResult], performance_summary: Dict[str, Any]) -> List[str]:
    """Generate optimization recommendations based on health check results"""
    recommendations = []

    # Check connection pool utilization
    pool_check = next((c for c in checks if c.name == "connection_pool"), None)
    if pool_check and pool_check.details:
        utilization = pool_check.details.get("utilization_percent", 0)
        if utilization > 80:
            recommendations.append("Consider increasing connection pool size")
        elif utilization < 20:
            recommendations.append("Connection pool may be oversized for current load")

    # Check query performance
    perf_check = next((c for c in checks if c.name == "query_performance"), None)
    if perf_check and perf_check.details:
        avg_duration = perf_check.details.get("average_duration_ms", 0)
        slow_queries = perf_check.details.get("slow_query_count", 0)

        if avg_duration > 500:
            recommendations.append("Consider optimizing slow queries or adding indexes")
        if slow_queries > 5:
            recommendations.append("Review and optimize frequently slow queries")

    # Check table statistics
    stats_check = next((c for c in checks if c.name == "table_statistics"), None)
    if stats_check and stats_check.details:
        issues = stats_check.details.get("issues", [])
        if issues:
            recommendations.extend([f"Address data issue: {issue}" for issue in issues])

    # Check locks
    locks_check = next((c for c in checks if c.name == "database_locks"), None)
    if locks_check and locks_check.details:
        waiting_locks = locks_check.details.get("waiting_locks", 0)
        if waiting_locks > 0:
            recommendations.append("Monitor for lock contention and optimize conflicting queries")

    if not recommendations:
        recommendations.append("Database performance appears optimal")

    return recommendations


# ============================================================================
# ASYNC HEALTH CHECKS (FOR WEB ENDPOINTS)
# ============================================================================


async def async_health_check() -> Dict[str, Any]:
    """Async version for web endpoints - runs basic checks only"""
    loop = asyncio.get_event_loop()

    # Run basic connectivity check in thread pool
    connectivity_check = await loop.run_in_executor(None, check_database_connectivity)
    pool_check = await loop.run_in_executor(None, check_connection_pool_health)

    checks = [connectivity_check, pool_check]

    # Determine overall status
    if any(c.status == "critical" for c in checks):
        overall_status = "critical"
    elif any(c.status == "warning" for c in checks):
        overall_status = "warning"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": [check.to_dict() for check in checks],
    }


# ============================================================================
# HEALTH CHECK ENDPOINT HELPERS
# ============================================================================


def get_quick_health_status() -> Dict[str, Any]:
    """Quick health check for monitoring systems"""
    try:
        connectivity = check_database_connectivity()

        return {
            "status": connectivity.status,
            "message": connectivity.message,
            "duration_ms": connectivity.duration_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "critical",
            "message": f"Health check failed: {str(e)}",
            "duration_ms": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }
