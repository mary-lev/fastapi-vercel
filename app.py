from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from routes import submission
from routes import users
from routes import solution
from routes import lesson
from routes import task_generator
from routes import topics
from routes import task
from routes import course
from routes import session
from routes import telegram_bot


### Create FastAPI instance with custom docs and OpenAPI URL
app = FastAPI(docs_url="/docs", openapi_url="/openapi.json")

origins = [
    "http://localhost:3000",  # Next.js frontend on port 3000
    "http://localhost:3001",  # If your frontend runs on port 3001
    "http://localhost:3002",  # If your frontend runs on port 3002
    "http://localhost:8000",  # FastAPI backend on port 8000
    "https://frontend-template-lilac.vercel.app",  # Vercel frontend address
    "https://dhdk.vercel.app",  # Vercel frontend address
    # Add any other origins that need access
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Use the list of specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(submission.router, tags=["Submissions"])
app.include_router(users.router, tags=["Users"])
app.include_router(solution.router, tags=["Solutions"])
app.include_router(lesson.router, tags=["Lessons"])
app.include_router(task_generator.router, tags=["Task Generator"])
app.include_router(topics.router, tags=["Topics"])
app.include_router(task.router, tags=["Tasks"])
app.include_router(course.router, tags=["Courses"])
app.include_router(session.router, tags=["Sessions"])
app.include_router(telegram_bot.router, tags=["Telegram Bot"])