# routes/session.py

import json
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models import User
from db import get_db
from utils.logging_config import logger
from schemas.validation import SessionRecordingSchema


router = APIRouter()


@router.post("/api/store-session")
async def store_session(request: Request):
    from uuid import uuid4

    id = str(uuid4())
    data = await request.json()
    with open(f"data/sessions/{id}.json", "w") as f:
        json.dump(data, f)


@router.post("/api/record-session")
async def record_session(session_data: SessionRecordingSchema, db: Session = Depends(get_db)):
    try:
        user_id = session_data.user_id
        events = session_data.events

        # Ensure the user exists
        user = db.query(User).filter(User.internal_user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Sessions are not stored in DB anymore. Persist to file for now.
        import uuid
        session_id = str(uuid.uuid4())
        with open(f"data/sessions/{session_id}.json", "w") as f:
            json.dump({"user_id": user_id, "events": events}, f)

        logger.info(f"Session recorded to file for user: {user_id}")
        return {"message": "Session recording saved", "session_id": session_id}

    except ValueError as e:
        logger.error(f"Validation error in record_session: {e}")
        raise HTTPException(status_code=400, detail="Invalid session data")
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in record_session: {e}")
        raise HTTPException(status_code=409, detail="Session recording conflict")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in record_session: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in record_session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/get-session")
async def get_session():
    from uuid import uuid4

    id = str(uuid4())
    try:
        with open(f"data/sessions/{id}.json", "r") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session file not found")
