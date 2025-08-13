import os
import re
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from db import SessionLocal  # Keep for backwards compatibility in utility files

from models import Lesson, Topic
from models import TrueFalseQuiz, MultipleSelectQuiz, CodeTask, SingleQuestionTask, Tag


from dotenv import load_dotenv
load_dotenv()


class TaskType(str, Enum):
    multiple_choice = "multiple_choice"
    # true_false = "true_false"
    # code = "code"
    single_question = "single_question"


class Task(BaseModel):
    type: TaskType
    name: str
    question: str = Field(description="Question for the student to answer. No code here")
    answer_choices: Optional[List[str]] = None
    correct_answers: Optional[List[str]] = Field(
        None, description="The ordered numbers of correct answers to the question."
    )
    code: Optional[str] = Field(
        None, description="Code snipper provided to a students that they are supposed to fix or continue."
    )
    points: int = Field(description="Points to acquire for the task solution")


class TaskGroup(BaseModel):
    tasks: List[Task]


# Mapping from task 'type' to 'lessonType'
type_mapping = {
    "multiple_choice": "MultipleSelectQuiz",
    # "true_false": "TrueFalse",
    "code": "Code",
    "single_question": "SingleQuestion",
}


# Function to process each task
task_model_mapping = {
    "MultipleSelectQuiz": MultipleSelectQuiz,
    "SingleSelectQuiz": MultipleSelectQuiz,  # Adjust this if needed for different models
    "TrueFalseQuiz": TrueFalseQuiz,
    "Code": CodeTask,
    "SingleQuestion": SingleQuestionTask,
}


def process_task(task, index, topic_id, db=None):
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    processed_task = {}
    task_type = task.type.value  # Get the string value of the TaskType enum
    lesson_type = type_mapping.get(task_type, "UnknownType")
    processed_task["lessonType"] = lesson_type

    # Generate lssonLink and lessonName based on task type and index
    if task_type == "code":
        # processed_task["lssonLink"] = f"code-task-{index+1}"
        processed_task["lessonName"] = task.name or "Coding Exercise"
    else:
        # processed_task["lssonLink"] = f"question-{index+1}"
        processed_task["lessonName"] = task.name or "Quiz Question"

    # Prepare the data field
    data = {}
    if lesson_type in ["MultipleSelectQuiz", "SingleSelectQuiz"]:
        data["question"] = task.question
        answer_choices = task.answer_choices or []
        # Map answer choices to options with ids
        options = []
        for i, choice in enumerate(answer_choices):
            options.append({"id": str(i + 1), "name": choice})
        data["options"] = options
        data["correctAnswers"] = task.correct_answers

    elif lesson_type == "Code":
        data["text"] = task.question
        data["code"] = task.code or "# Your code is here..."

    elif lesson_type == "SingleQuestion":
        data["question"] = task.question

    else:
        # Handle unknown types
        data["question"] = task.question

    processed_task["points"] = task.points
    processed_task["topic_id"] = topic_id
    processed_task["data"] = data

    # Add is_active = False field
    processed_task["is_active"] = False

    # Insert into the database
    task_model_class = task_model_mapping.get(lesson_type, Task)

    new_task = task_model_class(
        task_name=processed_task["lessonName"],
        task_link=str(index + 1),  # Use the index as the task link
        points=processed_task["points"],
        order=index + 1,  # Ensure the tasks are ordered
        topic_id=topic_id,
        data=processed_task["data"],
        is_active=False,  # Ensure is_active is set to False
    )

    # Add the task to the session and commit
    db.add(new_task)
    db.commit()

    if should_close:
        db.close()

    return processed_task


def extract_exercise_number(filename):
    match = re.search(r"exercise-(\d+)", filename)
    return int(match.group(1)) if match else float("inf")


def import_tasks(current_topic: int, db=None):
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False

    # Fetch the current topic
    current_topic = db.query(Topic).filter(Topic.id == current_topic).first()
    current_lesson = db.query(Lesson).filter(Lesson.id == current_topic.lesson_id).first()

    current_topic_title = current_topic.title
    name = current_topic_title.split(". ")
    folder = f"data/exercises/{name[0].lower()}/{name[1].lower()}"
    filenames = [filename for filename in os.listdir(folder) if filename.endswith(".md")]
    print(len(filenames))

    # Sort filenames by numeric part
    filenames = sorted(
        [filename for filename in os.listdir(folder) if filename.endswith(".md")], key=extract_exercise_number
    )
    print(filenames)

    # Ensure tags 'peroni' and 'beginner' exist in the database
    tags = {}
    for tag_name in ["peroni", "advanced"]:
        tag = db.query(Tag).filter_by(name=tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            db.add(tag)
            db.commit()
        tags[tag_name] = tag

    for task_order, filename in enumerate(filenames, start=1):
        # Read the content of each markdown file
        try:
            with open(f"{folder}/{filename}", "r") as f:
                task_content = f.read()
        except Exception as e:
            print(f"Error reading content from {filename}: {str(e)}")
            continue

        # Parse the task name
        task_name = filename.replace(".md", "")

        # Extract the task text section
        task_text_match = re.search(r"### Text\n(.*?)(?=\n### Solution|\Z)", task_content, re.DOTALL)
        task_text = task_text_match.group(1).strip() if task_text_match else "No task text found"

        # Extract the solution
        solution_match = re.search(r"### Solution\n`(.*?)`", task_content)
        correct_answer = solution_match.group(1).strip() if solution_match else None

        # Define the task link and order (based on filename or other criteria)
        task_link = filename.replace(".md", "")

        # Create a new SingleQuestionTask
        new_task = CodeTask(
            task_name=task_name.capitalize(),
            task_link=task_link,
            points=10,  # Define points or calculate if needed
            type="code_task",
            order=task_order,
            data={"text": task_text, "correct_answer": correct_answer},
            topic_id=current_topic.id,
            is_active=True,
        )
        new_task.tags.extend([tags["peroni"], tags["advanced"]])
        print(new_task.task_name)

        try:
            db.add(new_task)
            db.commit()
            print(f"Task '{task_name}' added successfully.")
        except SQLAlchemyError as e:
            db.rollback()
            print(f"Error saving task '{task_name}': {str(e)}")

    if should_close:
        db.close()

    # # Modify system prompt to include previous concepts
    # system_prompt = f'''
    #     We are importing exercises for the Python course from the markdown file into our database.
    #     Read the task content below and generate task items based on the content.
    #     Create the single_question task from the task content accordingly.
    #     Include the code provided in the task content in the question field.
    #     For the task title  use the {filename.replace(".md", "")}.
    # '''

    # # User prompt remains the same
    # user_prompt = f'''
    #     The task content is {task_content}.
    # '''

    # completion = client.beta.chat.completions.parse(
    #     model="gpt-4o-2024-08-06",
    #     messages=[
    #         {"role": "system", "content": system_prompt},
    #         {"role": "user", "content": user_prompt},
    #     ],
    #     temperature=0.7,
    #     response_format=Task
    # )
    # task = completion.choices[0].message.parsed
    # print(task)

    # list_items = []
    # for index, task in enumerate(tasks.tasks):
    #     processed_task = process_task(task, index, current_topic.id)
    #     list_items.append(processed_task)

    # print(list_items)
    # with open(f"data/tasks/topic_{current_topic}_tasks.json", "w") as file:
    #     json.dump(list_items, file, indent=4)

    # return list_items


if __name__ == "__main__":
    current_topic = 31
    import_tasks(current_topic)
