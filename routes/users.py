from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from db import get_db
from psycopg2.extras import RealDictCursor


router = APIRouter(prefix="/api/py")


@router.get("/users/")
def find_user(hashed_sub: str = None, internal_user_id: str = None, db=Depends(get_db)):
    if hashed_sub:
        query = "SELECT * FROM users WHERE hashed_sub = %s"
        param = hashed_sub
    elif internal_user_id:
        query = "SELECT * FROM users WHERE internal_user_id = %s"
        param = internal_user_id
    else:
        raise HTTPException(status_code=400, detail="Must provide either 'hashed_sub' or 'internal_user_id'")

    with db.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, (param,))
        user = cursor.fetchone()

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        return {"user": user}


# Endpoint to insert a new user
@router.post("/users/")
def insert_new_user(internal_user_id: str, hashed_sub: str, db=Depends(get_db)):
    cursor = db.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            INSERT INTO users (internal_user_id, hashed_sub)
            VALUES (%s, %s)
            RETURNING *;
        """, (internal_user_id, hashed_sub))
        new_user = cursor.fetchone()
        db.commit()
        return {"new_user": new_user}
    finally:
        cursor.close()
