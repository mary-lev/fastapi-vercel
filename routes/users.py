from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models import User, UserStatus  # Assuming you have a User model defined
from db import get_db
from passlib.hash import bcrypt
from utils.logging_config import logger
from utils.error_handling import (
    handle_database_error,
    validate_resource_exists,
    safe_database_operation,
    log_operation_success,
)
from schemas.validation import UserRegistrationSchema

router = APIRouter()


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
def register_user(data: UserRegistrationSchema, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.username == data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = bcrypt.hash(data.password)

    # Use centralized error handling for database operations
    try:
        with safe_database_operation(db, "user registration"):
            new_user = User(
                internal_user_id=data.username,
                username=data.username,
                hashed_sub=hashed_password,
                status=UserStatus.STUDENT,
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

        log_operation_success("User registration", f"Username: {data.username}")
        return {"message": "User registered successfully", "user": new_user}

    except Exception as e:
        handle_database_error(e, "user registration")


class LoginUser(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6)


@router.post("/users/login")
def login_user(data: LoginUser, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == data.username).first()

        if not user or not bcrypt.verify(data.password, user.hashed_sub):
            logger.warning(f"Failed login attempt for username: {data.username}")
            raise HTTPException(status_code=401, detail="Invalid username or password")

        logger.info(f"Successful login for user: {user.username}")
        return {
            "message": "Login successful",
            "user": {
                "username": user.username,
                "internal_user_id": user.internal_user_id,
                "status": user.status.value,
            },
        }
    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except SQLAlchemyError as e:
        logger.error(f"Database error in login_user: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        logger.error(f"Unexpected error in login_user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class UpdateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    currentPwd: str = Field(..., min_length=6)
    newPwd: str = Field(None, min_length=6)


@router.post("/users/update")
def update_user(data: UpdateUserRequest, db: Session = Depends(get_db)):
    try:
        # Find the user by the current username
        user = db.query(User).filter(User.username == data.username).first()

        if not user:
            logger.warning(f"Update attempt for non-existent user: {data.username}")
            raise HTTPException(status_code=404, detail="User not found")

        # Verify the current password
        if not bcrypt.verify(data.currentPwd, user.hashed_sub):
            logger.warning(f"Invalid password attempt for user update: {user.username}")
            raise HTTPException(status_code=401, detail="Current password is incorrect")

        # Update the username
        user.username = data.username

        # Update the password if a new one is provided
        if data.newPwd:
            user.hashed_sub = bcrypt.hash(data.newPwd)
            logger.info(f"Password updated for user: {user.username}")

        # Commit changes to the database
        db.commit()
        db.refresh(user)

        logger.info(f"User information updated successfully: {user.username}")
        return {"message": "User information updated successfully", "username": user.username}

    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in update_user: {e}")
        raise HTTPException(status_code=409, detail="Username already exists")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in update_user: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in update_user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
