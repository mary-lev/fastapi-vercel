from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models import Lesson, Topic, Task, Summary, TaskSolution, User, Course, CourseEnrollment
from db import get_db
from utils.logging_config import logger
from pydantic import BaseModel

router = APIRouter()


class EnrollmentRequest(BaseModel):
    course_id: int
    user_id: int


class EnrollmentResponse(BaseModel):
    status: str
    message: str
    enrollment_id: int = None


@router.get("/api/courses/{course_id}")
def get_course_data(course_id: int, db: Session = Depends(get_db)):
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            logger.warning(f"Course not found: {course_id}")
            raise HTTPException(status_code=404, detail="Course not found")

        logger.info(f"Course data retrieved: {course_id}")
    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_course_data: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        logger.error(f"Unexpected error in get_course_data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    return {
        "id": course.id,
        "courseTitle": course.title,
        "desc": course.description,
        "userImg": "/images/client/avatar-02.png",
        "userName": " Silvio Peroni ",
        "userCategory": "DHDK",
        "courseOverview": [
            {
                "title": "What you'll learn",
                "desc": "At the end of the course, the student knows the high-level principles, as well as the historical and theoretical backgrounds, for solving problems efficiently by using computational tools and information-processing agents. The student is able to understand and use the main data structures for organising information, to develop algorithms for addressing computational-related tasks, and to implement such algorithms in a specific programming language.",
                "descTwo": "The course is organised in a series of lectures. Each lecture introduces a specific topic, includes mentions to some related historical facts and to people (indicated between squared brackets) who have provided interesting insights on the subject. The lectures are accompanied by several hands-on sessions for learning the primary constructs of the programming language that will be used for implementing and running the various algorithms proposed.",
                "overviewList": [
                    {"listItem": "Understand and apply the principles of computational thinking and abstraction."},
                    {
                        "listItem": "Gain proficiency in Python programming, including variables, assignments, loops, and conditional statements."
                    },
                    {
                        "listItem": "Use Python data structures like lists, stacks, queues, sets, and dictionaries to organize and manipulate information.."
                    },
                    {
                        "listItem": "Implement various algorithms—including brute-force, recursive, divide and conquer, dynamic programming, and greedy algorithms—in Python."
                    },
                    {
                        "listItem": "Analyze the computational cost and complexity of algorithms to understand the limits of computation."
                    },
                    {
                        "listItem": "Apply algorithms to data structures such as trees and graphs to solve complex problems in the digital humanities."
                    },
                    {"listItem": "Develop and implement algorithms from scratch using flowcharts and pseudocode."},
                    {
                        "listItem": "Build a portfolio of Python programs that address computational tasks relevant to digital humanities projects.."
                    },
                ],
            }
        ],
        "courseContent": [
            {
                "title": "Course Content",
                "contentList": [
                    {
                        "id": lesson.id,
                        "title": lesson.title,
                        "time": lesson.start_date.strftime("%d/%m/%Y"),
                        "collapsed": False,
                        "isShow": True,
                        "expand": True,
                        "listItem": [
                            {
                                "text": topic.title,
                                "status": lesson.start_date <= datetime.now(),
                            }
                            for topic in lesson.topics
                        ],
                    }
                    for lesson in course.lessons
                ],
            }
        ],
        "courseRequirement": [
            {
                "title": "Requirements",
                "detailsList": [
                    {"listItem": "No prior programming experience needed."},
                    {"listItem": "Basic computer skills"},
                    {"listItem": "Interest in Digital Humanities"},
                    {"listItem": "Willingness to participate actively"},
                ],
            },
            {
                "title": "Description",
                "detailsList": [
                    {"listItem": "Learn the fundamentals of computational thinking and problem-solving."},
                    {"listItem": "Develop proficiency in Python programming from scratch."},
                    {"listItem": "Implement algorithms and data structures to organize and process information."},
                    {"listItem": "Apply computational methods to address tasks in the digital humanities."},
                ],
            },
        ],
        "courseInstructor": [
            {
                "title": "Professor",
                "body": [
                    {
                        "id": 1,
                        "img": "/images/client/avatar-02.png",
                        "name": "Silvio Peroni",
                        "type": "Director of Second Cycle Degree in Digital Humanities and Digital Knowledge",
                        "desc": "Associate Professor / Department of Classical Philology and Italian Studies",
                        "social": [
                            {"link": "https://x.com/essepuntato", "icon": "twitter"},
                            {"link": "https://www.linkedin.com/in/essepuntato/", "icon": "linkedin"},
                        ],
                    }
                ],
            }
        ],
    }


@router.post("/api/course/enroll", response_model=EnrollmentResponse)
async def enroll_user_in_course(enrollment_request: EnrollmentRequest, db: Session = Depends(get_db)):
    """
    Enroll a user in a course

    This endpoint handles course enrollment for users,
    typically called after successful Telegram authentication.
    """
    try:
        course_id = enrollment_request.course_id
        user_id = enrollment_request.user_id

        logger.info(f"Processing enrollment: user {user_id} -> course {course_id}")

        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        # Verify course exists
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            logger.warning(f"Course not found: {course_id}")
            raise HTTPException(status_code=404, detail="Course not found")

        # Check if already enrolled
        existing_enrollment = (
            db.query(CourseEnrollment)
            .filter(CourseEnrollment.user_id == user_id, CourseEnrollment.course_id == course_id)
            .first()
        )

        if existing_enrollment:
            logger.info(f"User {user_id} already enrolled in course {course_id}")
            return EnrollmentResponse(
                status="already_enrolled",
                message="User is already enrolled in this course",
                enrollment_id=existing_enrollment.id,
            )

        # Create new enrollment
        enrollment = CourseEnrollment(user_id=user_id, course_id=course_id)

        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)

        logger.info(f"Successfully enrolled user {user_id} in course {course_id}")

        return EnrollmentResponse(
            status="success", message="Successfully enrolled in course", enrollment_id=enrollment.id
        )

    except HTTPException:
        # Re-raise HTTPExceptions without modification
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error in enroll_user_in_course: {e}")

        # Check if this is a unique constraint violation
        if "course_enrollments" in str(e) and "user_id" in str(e):
            raise HTTPException(status_code=409, detail="User is already enrolled in this course")

        raise HTTPException(status_code=409, detail="Enrollment conflict occurred")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in enroll_user_in_course: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in enroll_user_in_course: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
