import os
import json
import requests
from enum import Enum
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field
from pydantic.class_validators import root_validator
from openai import OpenAI

from db import SessionLocal

from models import Lesson, Topic
from models import TrueFalseQuiz, MultipleSelectQuiz, CodeTask, SingleQuestionTask
from models import Task as TaskReady
from routes.topics import get_topic_data
from routes.lesson import rebuild_task_links

from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


class TaskType(str, Enum):
    multiple_choice = "multiple_choice"
    # true_false = "true_false"
    code = "code"
    single_question = "single_question"

class Task(BaseModel):
    type: TaskType
    name: str
    question: str = Field(description="Question for the student to answer. No code here")
    # answer_choices: Optional[List[str]] = None
    # correct_answers: Optional[List[str]] = Field(None, description="The ordered numbers of correct answers to the question.")
    code: Optional[str] = Field(None, description="Code snipper provided to a students that they are supposed to fix or continue.")
    points: int = Field(description="Points to acquire for the task solution, ranging from 5 to 15 depending on the task complexity."
    )

class TaskGroup(BaseModel):
    tasks: List[Task]


# Mapping from task 'type' to 'lessonType'
type_mapping = {
    "multiple_choice": "MultipleSelectQuiz",
    # "true_false": "TrueFalse",
    "code": "Code",
    "single_question": "SingleQuestion"
}


# Function to process each task
task_model_mapping = {
    "MultipleSelectQuiz": MultipleSelectQuiz,
    "SingleSelectQuiz": MultipleSelectQuiz,  # Adjust this if needed for different models
    "TrueFalseQuiz": TrueFalseQuiz,
    "Code": CodeTask,
    "SingleQuestion": SingleQuestionTask,
}

def process_task(task, index, topic_id):
    db = SessionLocal()
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
            options.append({
                "id": str(i+1),
                "name": choice
            })
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
        is_active=False  # Ensure is_active is set to False
    )
    
    # Add the task to the session and commit
    db.add(new_task)
    db.commit()

    return processed_task


suggested_material = [
        "Harry Potter",
        "classical italian literature",
        "Jane Austen",
        "tv series",
        "Game of Thrones",
        "Lord of the Rings",
        "Star Wars",
        "The Simpsons",
        "video games",
    ]

def generate_tasks(
    topic_id: int = 11,
    num_tasks: int = 5,
    add_quizzes: bool = False,
    add_previous_tasks: bool = True,
    material: str = "Harry Potter",
):
    db = SessionLocal()

    # Fetch the current topic
    current_topic = db.query(Topic).filter(Topic.id == topic_id).first()
    current_lesson = db.query(Lesson).filter(Lesson.id == current_topic.lesson_id).first()

    # Fetch all previous lessons in the course (including the current lesson)
    previous_lessons = db.query(Lesson).filter(
        Lesson.course_id == current_lesson.course_id,
        Lesson.lesson_order < current_lesson.lesson_order  # Lessons before or same as current one
    ).order_by(Lesson.lesson_order).all()

    previous_concepts = []
    for lesson in previous_lessons:
        lesson_topics = db.query(Topic).filter(Topic.lesson_id == lesson.id).order_by(Topic.topic_order).all()
        for topic in lesson_topics:
            if topic.concepts:
                previous_concepts.append(topic.concepts)

    # Add the earliest topics of the current lesson (up to the current topic's order)
    earliest_topics = db.query(Topic).filter(
        Topic.lesson_id == current_lesson.id,
        Topic.topic_order <= current_topic.topic_order  # Only topics up to the current one
    ).order_by(Topic.topic_order).all()

    for topic in earliest_topics:
        if topic.concepts and topic not in previous_concepts:
            previous_concepts.append(topic.concepts)

    # Combine all collected concepts from previous lessons and topics
    previous_concepts_text = " ".join(previous_concepts)
    text_about_previous_concepts = f"Students have already learned the following concepts from previous lessons: {previous_concepts_text}"
    print(text_about_previous_concepts)

    # Read the content of the current topic
    try:
        with open(f"data/textbook/{current_topic.content_file_md}", "r") as f:
            topic_content = f.read()
    except:
        with open(f"data/lectures/{current_lesson.id}.txt", "r") as f:
            topic_content = f.read()

    starting_text = f'''
        We are creating the set of tasks for the graduate students in the Digital Humanities program learning their first Python course.
        Create tasks for the student that help them train their understanding of the topic, following this specific structure:
    '''

    if previous_concepts:
        starting_text += text_about_previous_concepts
    else:
        starting_text += "This is the first lesson in the course. Student don't have any previous knowledge about the course content."
    
    if add_previous_tasks:
        print("Adding previous tasks")
        task_data = get_topic_data(topic_id)
        #questions = [task["question"] for task in task_data.get("tasks", [])]
        texts = [task["text"] for task in task_data.get("tasks", []) if task.get("type") == "code_task"]
        starting_text += f'''
            We already have the following tasks for this lesson:
            {texts}
        '''
    
    if add_quizzes:
        starting_text += "**Understanding Check:** Begin with multiple-choice question to assess students' understanding of the lesson content."
    
    structure_description = f'''
        **Instructions:**
        - Create the coding tasks for the topic {current_topic.title}.
        - The first task has to check the common understanding of the topic. Students write simple code using the new concepts.
        - Then add a debugging tasks to train student's problem-solving skills, accuracy and attention to detail.
        - Add a set of coding tasks that progress in complexity.
        - And the last complex coding task has to challenge students and test their ability to apply the new concepts.

        **Task Structure:**
        - Ensure tasks are directly aligned with the topic’s content and learning objectives.
        - Tasks should match the students’ skill level, progressing from simple to complex.
        - Integrate real-world Digital Humanities examples, such as text analysis, historical datasets, or cultural artifact processing, where appropriate.
        - Scaffold the tasks, providing more guidance initially, and reducing it as tasks increase in complexity to encourage independent thinking.
        - Provide clear evaluation criteria for each task, explaining what a correct answer should include.
        - Keep all tasks concise, focused, and engaging.
    '''

    if material:
        starting_text += f'''
            **Suggested Material:** Use the {material} material to create tasks that are engaging and relevant to the students.  
        '''

    # Modify system prompt to include previous concepts
    system_prompt = f'''
        {starting_text}
        {structure_description}      
    '''
    print(system_prompt)
    
    # User prompt remains the same
    user_prompt = f'''
        Generate {num_tasks} tasks for this part of the lesson following the instructions above.
        Be aware that the task solution need only the concepts mentioned in the topic content.
        Tasks have to include the main concepts of the topic: {current_topic.concepts}.
        The students had to read this textbook chapter: {topic_content}.
    '''
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            response_format=TaskGroup,
        )
    except Exception as e:
        print(e)
        return []

    tasks = completion.choices[0].message.parsed

    list_items = []
    for index, task in enumerate(tasks.tasks):
        processed_task = process_task(task, index, current_topic.id)
        list_items.append(processed_task)

    with open(f"data/tasks/topic_{topic_id}_tasks.json", "w") as file:
        json.dump(list_items, file, indent=4)
    
    rebuild_task_links(current_lesson.id)

    return list_items

# generate_tasks(19, 5)