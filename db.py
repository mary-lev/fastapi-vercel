from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings  # Import is needed here
from base import Base

# Enable pool_pre_ping to prevent stale connections
engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True)  # Check if connection is alive before using it

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
