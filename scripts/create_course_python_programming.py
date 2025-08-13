"""One-off script to promote a user to professor and create a new course.

Usage:
  Run from the project root with the virtual environment activated, e.g.:
    python scripts/create_course_python_programming.py
"""

from typing import Optional
import sys
import os

# Ensure project root is on the import path when running as a script
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db import SessionLocal
from models import User, UserStatus, Course
from sqlalchemy import text


TARGET_USER_ID: int = 73
COURSE_TITLE: str = "Python Programming"
COURSE_DESCRIPTION: str = "A comprehensive introduction to Python programming."


def promote_user_to_professor_if_needed(db) -> Optional[User]:
    user: Optional[User] = db.query(User).filter(User.id == TARGET_USER_ID).first()
    if user is None:
        print(f"User with id {TARGET_USER_ID} not found.")
        return None

    if user.status != UserStatus.PROFESSOR:
        user.status = UserStatus.PROFESSOR
        db.add(user)
        print(f"Promoted user {TARGET_USER_ID} to professor.")
    else:
        print(f"User {TARGET_USER_ID} is already a professor.")

    return user


def create_course(db, professor_id: int) -> Course:
    existing = (
        db.query(Course)
        .filter(Course.title == COURSE_TITLE, Course.professor_id == professor_id)
        .first()
    )
    if existing:
        print(
            f"Course '{COURSE_TITLE}' already exists with id {existing.id} for professor {professor_id}. Skipping create."
        )
        return existing

    new_course = Course(title=COURSE_TITLE, description=COURSE_DESCRIPTION, professor_id=professor_id)
    db.add(new_course)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        msg = str(exc)
        # Attempt to fix possible sequence mismatch for courses.id
        if "courses_pkey" in msg or "duplicate key value" in msg:
            max_id = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM courses")).scalar() or 0
            # Use pg_get_serial_sequence to be robust to non-default sequence names
            db.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('courses','id'), :newval)"
                ),
                {"newval": max_id},
            )
            db.commit()
            # Retry once
            db.add(new_course)
            db.commit()
        else:
            raise

    db.refresh(new_course)
    print(f"Created course '{COURSE_TITLE}' with id {new_course.id} for professor {professor_id}.")
    return new_course


def main() -> None:
    db = SessionLocal()
    try:
        user = promote_user_to_professor_if_needed(db)
        if user is None:
            db.rollback()
            return

        # Ensure any user status change is persisted before creating the course
        db.commit()

        create_course(db, professor_id=user.id)
    except Exception as exc:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()


