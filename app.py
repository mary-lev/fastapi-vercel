from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from routes import submission
from routes import users
from routes import solution
from routes import lesson


### Create FastAPI instance with custom docs and OpenAPI URL
app = FastAPI(docs_url="/docs", openapi_url="/openapi.json")

origins = [
    "http://localhost:3000",  # Next.js frontend on port 3000
    "http://localhost:3001",  # If your frontend runs on port 3001
    "http://localhost:3002",  # If your frontend runs on port 3002
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

app.include_router(submission.router)
app.include_router(users.router)
app.include_router(solution.router)
app.include_router(lesson.router)
