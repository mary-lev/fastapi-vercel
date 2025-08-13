# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Local Development
- **Run the application**: `uvicorn app:app --reload`
- **Install dependencies**: `pip install -r requirements.txt`
- **Create virtual environment**: `python -m venv venv && source venv/bin/activate`

### Database Operations
- **Run migrations**: `alembic upgrade head`
- **Create new migration**: `alembic revision --autogenerate -m "description"`
- **Downgrade migration**: `alembic downgrade -1`

### Deployment
- **Deploy to Vercel**: `vercel` or push to main branch for auto-deployment
- **Local Vercel dev**: `vercel dev`

### Code Quality
- **Format code**: `black . --line-length 120`
- **Lint code**: `ruff check .`

## Architecture Overview

This is a FastAPI-based educational platform deployed on Vercel with PostgreSQL database integration.

### Core Structure
- **app.py**: Main FastAPI application with CORS middleware and router includes
- **models.py**: SQLAlchemy ORM models for all database entities
- **schemas.py**: Pydantic models for API request/response validation
- **db.py**: Database connection setup using SQLAlchemy
- **config.py**: Environment configuration using pydantic-settings

### Database Architecture
The application uses a polymorphic task system with SQLAlchemy:

- **Base Task Model**: `Task` class with polymorphic inheritance
- **Task Types**: `CodeTask`, `TrueFalseQuiz`, `MultipleSelectQuiz`, `SingleQuestionTask`
- **Course Structure**: `Course` → `Lesson` → `Topic` → `Task`
- **User System**: Users with roles (student, professor, admin)
- **Progress Tracking**: `TaskAttempt`, `TaskSolution`, `AIFeedback` models

### Key Features
- **Task Management**: Polymorphic task system supporting multiple question types
- **User Authentication**: Hash-based user identification system
- **AI Integration**: OpenAI API integration for automated feedback
- **Session Recording**: User interaction tracking
- **Telegram Bot**: Bot integration for notifications
- **Alembic Migrations**: Database schema versioning

### Route Organization
Routes are organized by domain in the `routes/` directory:
- `task.py`: Task CRUD operations
- `users.py`: User management
- `course.py`, `lesson.py`, `topics.py`: Course structure
- `submission.py`, `solution.py`: Task submissions
- `telegram_bot.py`: Bot endpoints
- `session.py`: Session recording
- `task_generator.py`: AI-powered task generation

### Environment Setup
The application expects these environment variables in `.env.development`:
- `OPENAI_API_KEY`: OpenAI API access
- `POSTGRES_*`: Database connection parameters
- `NODE_ENV`: Environment identifier

### Data Storage
- **Static Content**: Educational content stored in `data/` directory
- **Exercises**: Structured by difficulty (beginner/intermediate/advanced)
- **Sessions**: JSON-based session recordings in `data/sessions/`

### Deployment Configuration
- **Vercel**: Configured via `vercel.json` for serverless Python deployment
- **CORS**: Configured for multiple frontend origins including localhost and Vercel domains