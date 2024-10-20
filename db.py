from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings  # Import is needed here
from base import Base

engine = create_engine(settings.POSTGRES_URL)  # Use the POSTGRES_URL from settings

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
