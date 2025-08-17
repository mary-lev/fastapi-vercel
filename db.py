import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from config import settings  # Import is needed here

# Import logging for connection monitoring
from utils.structured_logging import get_logger, LogCategory
from utils.query_monitor import pool_monitor

logger = get_logger("database")

# Test-friendly engine: use SQLite when NODE_ENV=test
if os.getenv("NODE_ENV") == "test":
    test_db_url = os.getenv("SQLALCHEMY_TEST_DATABASE_URL", "sqlite:///./test.db")
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    # Auto-create tables for tests
    try:
        from models import Base  # Local import to avoid circular during prod startup

        Base.metadata.create_all(bind=engine)
    except Exception:
        pass
else:
    # Optimized PostgreSQL connection configuration
    engine = create_engine(
        settings.POSTGRES_URL,
        # Connection pool configuration for high performance
        poolclass=QueuePool,
        pool_size=20,  # Number of connections to maintain in the pool
        max_overflow=30,  # Additional connections beyond pool_size
        pool_pre_ping=True,  # Validate connections before use
        pool_recycle=3600,  # Recycle connections every hour
        pool_timeout=30,  # Timeout for getting connection from pool
        # Query optimization settings
        echo=False,  # Set to True for SQL debugging (disable in production)
        echo_pool=False,  # Connection pool debugging
        # Performance optimizations
        connect_args={
            "connect_timeout": 10,
            "application_name": "educational_platform_api",
        },
    )


# Add connection pool monitoring
@event.listens_for(engine, "connect")
def set_postgresql_settings(dbapi_connection, connection_record):
    """Configure connection-level settings"""
    if not os.getenv("NODE_ENV") == "test":
        try:
            # PostgreSQL-specific optimizations
            with dbapi_connection.cursor() as cursor:
                # Set statement timeout to prevent runaway queries
                cursor.execute("SET statement_timeout = '30s'")
                # Optimize for OLTP workload
                cursor.execute("SET random_page_cost = 1.1")
                # Enable parallel workers for complex queries
                cursor.execute("SET max_parallel_workers_per_gather = 2")
        except Exception as e:
            # Log but don't fail if PostgreSQL-specific settings can't be applied
            logger.warning(f"Could not apply PostgreSQL settings: {e}", category=LogCategory.DATABASE)


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout for monitoring"""
    # Update pool monitor
    pool_monitor.update_pool_stats(engine)

    try:
        # Get invalidated count safely
        try:
            invalidated = engine.pool.invalidated()
        except (AttributeError, TypeError):
            try:
                invalidated = len(engine.pool._invalidated)
            except AttributeError:
                invalidated = 0

        logger.debug(
            "Database connection checked out",
            category=LogCategory.DATABASE,
            extra={
                "pool_size": engine.pool.size(),
                "checked_out": engine.pool.checkedout(),
                "overflow": engine.pool.overflow(),
                "invalidated": invalidated,
            },
        )
    except Exception as e:
        logger.debug(f"Pool monitoring error: {e}", category=LogCategory.DATABASE)


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log connection checkin for monitoring"""
    # Update pool monitor
    pool_monitor.update_pool_stats(engine)

    try:
        logger.debug(
            "Database connection checked in",
            category=LogCategory.DATABASE,
            extra={"pool_size": engine.pool.size(), "checked_out": engine.pool.checkedout()},
        )
    except Exception as e:
        logger.debug(f"Pool monitoring error: {e}", category=LogCategory.DATABASE)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
