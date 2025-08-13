import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings  # Import is needed here

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
    # Enable pool_pre_ping to prevent stale connections
    engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
