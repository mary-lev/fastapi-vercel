from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from utils.checker import run_code
from utils.evaluator import evaluate_code_submission

router = APIRouter(prefix="/api/py")

class CodeSubmission(BaseModel):
    code: str
    language: str
    task_id: int
    username: str
    # output: str = None

@router.post("/compile")
async def compile(code_submission: dict):
    print(code_submission)
    return run_code(code_submission["code"])


@router.post("/submit")
async def submit(code_submission: dict):
    user = {
        "username": "test",
        "id": 1
    }
    print(code_submission)
    task = code_submission["lessonItem"].get("data")
    result = run_code(code_submission["code"])
    if not result["success"]:
        return JSONResponse(content={"message": "Code submission failed", "result": result}, status_code=400)
    evaluation = evaluate_code_submission(code_submission, result["output"], task)
    return evaluation