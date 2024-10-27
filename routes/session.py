# routes/session.py

import json
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
from models import SessionRecording, User
from db import SessionLocal


router = APIRouter()

@router.post("/api/store-session")
async def store_session(request: Request):
    from uuid import uuid4
    id = str(uuid4())
    data = await request.json()
    with open(f"data/sessions/{id}.json", "w") as f:
        json.dump(data, f)


@router.post("/api/record-session")
async def record_session(request: Request):
    db: Session = SessionLocal()
    try:
        data = await request.json()
        
        user_id = data.get("userId")
        events = data.get("events")

        if not user_id or not events:
            raise HTTPException(status_code=400, detail="Missing user ID or events")

        # Ensure the user exists
        user = db.query(User).filter(User.internal_user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Save session recording
        session_recording = SessionRecording(
            user_id=user.id,
            events=events
        )
        db.add(session_recording)
        db.commit()

        return {"message": "Session recording saved successfully"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save session recording: {str(e)}")
    
    finally:
        db.close()


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
