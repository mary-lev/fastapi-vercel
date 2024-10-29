from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from models import User, UserStatus  # Assuming you have a User model defined
from db import get_db, SessionLocal
from passlib.hash import bcrypt

router = APIRouter()


class RegisterUser(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6)


# @router.get("/users/")
# def find_user(
#     hashed_sub: str = None,
#     internal_user_id: str = None,
#     username: str = None,
#     db: Session = Depends(get_db)
# ):
#     if not (hashed_sub or internal_user_id):
#         raise HTTPException(status_code=400, detail="Must provide 'hashed_sub' or 'internal_user_id'")
    
#     if hashed_sub:
#         user = db.query(User).filter(User.hashed_sub == hashed_sub).first()
#     elif internal_user_id:
#         user = db.query(User).filter(User.internal_user_id == internal_user_id).first()
#     elif username:
#         user = db.query(User).filter(User.username == username).first()

#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     return {"user": user}


# @router.post("/users/")
# def insert_new_user(
#     internal_user_id: str,
#     hashed_sub: str,
#     username: str,
#     db: Session = Depends(get_db)
# ):
#     try:
#         new_user = User(
#             internal_user_id=internal_user_id, 
#             hashed_sub=hashed_sub, 
#             username=username,
#             status=UserStatus.STUDENT
#         )
#         db.add(new_user)
#         db.commit()
#         db.refresh(new_user)
#         return {"new_user": new_user}
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/register")
def register_user(data: RegisterUser, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = bcrypt.hash(data.password)
    try:
        new_user = User(
            internal_user_id=data.username,
            username=data.username,
            hashed_sub=hashed_password,
            status=UserStatus.STUDENT,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "User registered successfully", "user": new_user}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


class LoginUser(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6)


@router.post("/users/login")
def login_user(data: LoginUser):
    db = SessionLocal()
    user = db.query(User).filter(User.username == data.username).first()

    if not user or not bcrypt.verify(data.password, user.hashed_sub):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {"message": "Login successful", "user": {
        "username": user.username,
        "internal_user_id": user.internal_user_id,
        "status": user.status.value,
        }}

class UpdateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    currentPwd: str = Field(..., min_length=6)
    newPwd: str = Field(None, min_length=6)

@router.post("/users/update")
def update_user(data: UpdateUserRequest):
    db = SessionLocal()
    # Find the user by the current username
    user = db.query(User).filter(User.username == data.username).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify the current password
    if not bcrypt.verify(data.currentPwd, user.hashed_sub):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    # Update the username
    user.username = data.username

    # Update the password if a new one is provided
    if data.newPwd:
        user.hashed_sub = bcrypt.hash(data.newPwd)

    # Commit changes to the database
    db.commit()
    db.refresh(user)

    return {"message": "User information updated successfully", "username": user.username}