from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Enum, Boolean, JSON
from sqlalchemy import Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

# Existing Enums and Models

class UserStatus(enum.Enum):
    STUDENT = "student"
    PROFESSOR = "professor"
    ADMIN = "admin"

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    internal_user_id = Column(String, index=True)
    hashed_sub = Column(String, unique=True, index=True)
    username = Column(String, unique=False, index=True, default="Anonymous") 
    status = Column(Enum(UserStatus), index=True, nullable=True)


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # Tag name, e.g., "easy", "data analysis"


task_tags = Table(
    'task_tags',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

# Polymorphic Task Model
class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    task_name = Column(String, nullable=False)
    task_link = Column(String, nullable=False, index=True)  # Task identifier
    points = Column(Integer, nullable=True)  # Points achievable for the task
    type = Column(String(50), nullable=False)  # Discriminator for task types
    order = Column(Integer, nullable=False)  # Order within the topic
    data = Column(JSON, nullable=False) 
    topic_id = Column(Integer, ForeignKey('topics.id'), nullable=False)  # Foreign key to Topic
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'task'
    }

    tags = relationship('Tag', secondary=task_tags, backref='tasks')


class TrueFalseQuiz(Task):
    __tablename__ = 'true_false_quizzes'
    id = Column(Integer, ForeignKey('tasks.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'true_false_quiz'
    }

class MultipleSelectQuiz(Task):
    __tablename__ = 'multiple_select_quizzes'
    id = Column(Integer, ForeignKey('tasks.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'multiple_select_quiz'
    }

class CodeTask(Task):
    __tablename__ = 'code_tasks'
    id = Column(Integer, ForeignKey('tasks.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'code_task'
    }

class SingleQuestionTask(Task):
    __tablename__ = 'single_question_tasks'
    id = Column(Integer, ForeignKey('tasks.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'single_question_task'
    }


class TaskAttempt(Base):
    __tablename__ = 'task_attempts'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    submitted_at = Column(DateTime, default=func.now(), nullable=False)
    is_successful = Column(Boolean, default=False)
    attempt_content = Column(String, nullable=True)

    user = relationship('User', backref='task_attempts')
    task = relationship('Task', backref='attempts')

# TaskSolution after successful attempt
class TaskSolution(Base):
    __tablename__ = 'task_solutions'
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    solution_content = Column(String)  # Could be code, quiz answers, etc.
    completed_at = Column(DateTime, default=func.now(), nullable=False)

    user = relationship('User', backref='task_solutions')
    task = relationship('Task', backref='solutions')

# Existing Models for Courses, Lessons, etc.
class Course(Base):
    __tablename__ = 'courses'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    professor_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    lessons = relationship('Lesson', back_populates='course')  # Add this line

class Lesson(Base):
    __tablename__ = 'lessons'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    lesson_order = Column(Integer, nullable=False)
    textbook = Column(String, nullable=True)
    start_date = Column(DateTime, nullable=True, default=func.now())

    topics = relationship("Topic", order_by="Topic.topic_order", back_populates="lesson")
    course = relationship('Course', back_populates='lessons')  # Add this line


class Topic(Base):
    __tablename__ = 'topics'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    background = Column(String, index=True)
    objectives = Column(String, index=True)
    content_file_md = Column(String, index=True)
    concepts = Column(String, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    lesson_id = Column(Integer, ForeignKey('lessons.id'), nullable=False)
    topic_order = Column(Integer, nullable=False)

    lesson = relationship('Lesson', back_populates='topics')  # Add this line
    tasks = relationship('Task', backref='topic', lazy='dynamic', order_by='Task.order')
    summary = relationship('Summary', uselist=False, back_populates='topic')


class Summary(Base):
    __tablename__ = 'summaries'

    id = Column(Integer, primary_key=True, index=True)
    lesson_name = Column(String, nullable=False)
    lesson_link = Column(String, nullable=False, unique=True)
    lesson_type = Column(String, default="Summary", nullable=False)
    icon_file = Column(String, nullable=True)
    data = Column(JSON, nullable=False)  # Storing description, items, textbooks in JSON
    topic_id = Column(Integer, ForeignKey('topics.id'), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationship with Topic
    topic = relationship('Topic', back_populates='summary')
