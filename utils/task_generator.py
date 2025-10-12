import os
import json
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI

from db import SessionLocal  # Keep for backwards compatibility in utility files

from models import Lesson, Topic, Task as DBTask
from models import TrueFalseQuiz, MultipleSelectQuiz, CodeTask, SingleQuestionTask
from sqlalchemy import func

# Removed missing imports - functions implemented locally

from dotenv import load_dotenv
from utils.structured_logging import get_logger

load_dotenv()


# Local implementations of missing functions
def get_topic_data(topic_id: int):
    """Get topic data with tasks for context generation"""
    db = SessionLocal()
    try:
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            return {"tasks": []}

        tasks = []
        for task in topic.tasks:
            task_data = {
                "id": task.id,
                "type": task.type,
                "text": task.task_name,
            }
            if hasattr(task, "data") and task.data:
                task_data.update(task.data)
            tasks.append(task_data)

        return {"tasks": tasks}
    finally:
        db.close()


def rebuild_task_links(lesson_id: int):
    """Rebuild task links to ensure unique IDs within the lesson"""
    db = SessionLocal()
    try:
        # Import here to avoid circular imports
        from models import Topic, Task

        # Get all topics in the lesson, ordered by topic_order
        topics = db.query(Topic).filter(Topic.lesson_id == lesson_id).order_by(Topic.topic_order).all()

        for topic in topics:
            # Get all tasks in the topic, ordered by order
            tasks = db.query(Task).filter(Task.topic_id == topic.id).order_by(Task.order).all()

            # Regenerate task_link for each task
            for task_index, task in enumerate(tasks):
                new_task_link = f"{topic.id}-{task_index + 1}"
                task.task_link = new_task_link

        db.commit()
    finally:
        db.close()


logger = get_logger("task_generator")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def get_language_instruction(language: str) -> str:
    """Get language-specific instruction for AI prompts"""
    if language and language.lower() == "russian":
        return "IMPORTANT: Generate all tasks, questions, instructions, and explanations in RUSSIAN language. Use proper Russian grammar and vocabulary appropriate for programming education."
    else:
        return "IMPORTANT: Generate all tasks, questions, instructions, and explanations in ENGLISH language."


client = OpenAI(api_key=OPENAI_API_KEY)


class TaskType(str, Enum):
    multiple_choice = "multiple_choice"
    # true_false = "true_false"
    code = "code"
    single_question = "single_question"


class Task(BaseModel):
    type: TaskType
    task_name: str
    question: str = Field(description="Question for the student to answer. No code here")
    answer_choices: Optional[List[str]] = Field(
        None, description="List of answer choices for multiple choice questions"
    )
    correct_answers: Optional[List[str]] = Field(None, description="The correct answers for multiple choice questions")
    code: Optional[str] = Field(
        None, description="Code snipper provided to a students that they are supposed to fix or continue."
    )
    points: int = Field(
        description="Points to acquire for the task solution, ranging from 5 to 15 depending on the task complexity."
    )


class TaskGroup(BaseModel):
    tasks: List[Task]


class AdaptiveTask(BaseModel):
    """Single adaptive task generated to address specific learning gaps"""

    type: TaskType
    name: str
    question: str = Field(description="Question text that addresses the specific learning gap")
    code: Optional[str] = Field(None, description="Code snippet if this is a code task")
    explanation: str = Field(description="Brief explanation of what skill this task trains")
    difficulty_adjustment: str = Field(description="How this task adjusts difficulty compared to the original")
    points: int = Field(description="Points (5-15) based on complexity and remediation needs")


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
        processed_task["lessonName"] = task.task_name or "Coding Exercise"
    else:
        # processed_task["lssonLink"] = f"question-{index+1}"
        processed_task["lessonName"] = task.task_name or "Quiz Question"

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

        # Convert correct answers from strings to option IDs (indices)
        correct_answer_ids = []
        if task.correct_answers:
            for correct_answer in task.correct_answers:
                # Find the matching option by text and get its ID
                for option in options:
                    if option["name"] == correct_answer:
                        correct_answer_ids.append(option["id"])
                        break
        data["correctAnswers"] = correct_answer_ids

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
    task_model_class = task_model_mapping.get(lesson_type, DBTask)

    # Get the current count of tasks in this topic to ensure proper ordering
    existing_task_count = db.query(DBTask).filter(DBTask.topic_id == topic_id).count()
    task_order = existing_task_count + index + 1

    new_task = task_model_class(
        task_name=processed_task["lessonName"],
        task_link=f"{topic_id}-{task_order}",  # Use proper topic_id-task_number format with global counting
        points=processed_task["points"],
        order=task_order,  # Ensure the tasks are ordered properly
        topic_id=topic_id,
        data=processed_task["data"],
        is_active=False,  # Ensure is_active is set to False
        attempt_strategy="unlimited",  # Ensure all tasks have unlimited attempts
        max_attempts=None,  # NULL = unlimited
    )

    # Add the task to the session and commit
    db.add(new_task)
    db.commit()

    if should_close:
        db.close()

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
    include_previous_lessons: bool = True,
    include_previous_topics: bool = True,
    custom_instructions: str = "",
    db=None,
):
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False

    # Fetch the current topic, lesson, and course
    current_topic = db.query(Topic).filter(Topic.id == topic_id).first()
    current_lesson = db.query(Lesson).filter(Lesson.id == current_topic.lesson_id).first()
    from models import Course

    current_course = db.query(Course).filter(Course.id == current_lesson.course_id).first()

    # Build previous concepts list based on context options
    previous_concepts = []

    # Include concepts from previous lessons if requested
    if include_previous_lessons:
        previous_lessons = (
            db.query(Lesson)
            .filter(
                Lesson.course_id == current_lesson.course_id,
                Lesson.lesson_order < current_lesson.lesson_order,
            )
            .order_by(Lesson.lesson_order)
            .all()
        )

        for lesson in previous_lessons:
            lesson_topics = db.query(Topic).filter(Topic.lesson_id == lesson.id).order_by(Topic.topic_order).all()
            for topic in lesson_topics:
                if topic.concepts:
                    previous_concepts.append(topic.concepts)

    # Include concepts from previous topics in current lesson if requested
    if include_previous_topics:
        earliest_topics = (
            db.query(Topic)
            .filter(
                Topic.lesson_id == current_lesson.id,
                Topic.topic_order < current_topic.topic_order,  # Only topics BEFORE current one
            )
            .order_by(Topic.topic_order)
            .all()
        )

        for topic in earliest_topics:
            if topic.concepts and topic.concepts not in previous_concepts:
                previous_concepts.append(topic.concepts)

    # Combine all collected concepts from previous lessons and topics
    previous_concepts_text = " ".join(previous_concepts)
    text_about_previous_concepts = (
        f"Students have already learned the following concepts from previous lessons: {previous_concepts_text}"
    )
    print(text_about_previous_concepts)

    # Read the content of the current topic
    topic_content = ""
    try:
        # Try to read from the content file path (handle both relative and absolute paths)
        content_path = current_topic.content_file_md
        if content_path:
            # If it's an absolute path, use it directly
            if content_path.startswith("/"):
                with open(content_path, "r") as f:
                    topic_content = f.read()
            # If path already starts with data/, use it as-is
            elif content_path.startswith("data/"):
                with open(content_path, "r") as f:
                    topic_content = f.read()
            else:
                # If it's just a filename, try different base directories
                try:
                    with open(f"data/textbook/{content_path}", "r") as f:
                        topic_content = f.read()
                except:
                    with open(f"data/tasks-2025/{content_path}", "r") as f:
                        topic_content = f.read()
        else:
            # Fallback to lesson-based content (if it exists)
            try:
                with open(f"data/lectures/{current_lesson.id}.txt", "r") as f:
                    topic_content = f.read()
            except FileNotFoundError:
                # Use topic information directly if no content file available
                topic_content = f"Topic: {current_topic.title}\n\nBackground: {current_topic.background or 'No background provided'}\n\nObjectives: {current_topic.objectives or 'No objectives provided'}\n\nConcepts: {current_topic.concepts or 'No concepts provided'}"
    except Exception as e:
        # If all else fails, use topic information directly
        logger.warning(f"Failed to read content file for topic {topic_id}: {str(e)}")
        topic_content = f"Topic: {current_topic.title}\n\nBackground: {current_topic.background or 'No background provided'}\n\nObjectives: {current_topic.objectives or 'No objectives provided'}\n\nConcepts: {current_topic.concepts or 'No concepts provided'}"

    starting_text = f"""
        We are creating the set of tasks for the graduate students in the Digital Humanities program learning their first Python course.
        Create tasks for the student that help them train their understanding of the topic, following this specific structure:
    """

    if previous_concepts:
        starting_text += text_about_previous_concepts
    else:
        starting_text += "This is the first lesson in the course. Student don't have any previous knowledge about the course content."

    if add_previous_tasks:
        print("Adding previous tasks")
        task_data = get_topic_data(topic_id)
        # questions = [task["question"] for task in task_data.get("tasks", [])]
        texts = [task["text"] for task in task_data.get("tasks", []) if task.get("type") == "code_task"]
        starting_text += f"""
            We already have the following tasks for this lesson:
            {texts}
        """

    if add_quizzes:
        starting_text += "**Understanding Check:** Begin with multiple-choice question to assess students' understanding of the lesson content."

    structure_description = f"""
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
    """

    if material:
        starting_text += f"""
            **Suggested Material:** Use the {material} material to create tasks that are engaging and relevant to the students.
        """

    # Add custom instructions if provided
    if custom_instructions:
        starting_text += f"""
            **Custom Instructions from Professor:** {custom_instructions}
        """

    # Get language instruction based on course language
    language_instruction = get_language_instruction(current_course.language if current_course else "English")

    # Modify system prompt to include previous concepts and language instruction
    system_prompt = f"""
        {language_instruction}

        {starting_text}
        {structure_description}
    """
    print(system_prompt)

    # User prompt remains the same
    user_prompt = f"""
        Generate {num_tasks} tasks for this part of the lesson following the instructions above.
        Be aware that the task solution need only the concepts mentioned in the topic content.
        Tasks have to include the main concepts of the topic: {current_topic.concepts}.
        The students had to read this textbook chapter: {topic_content}.
    """
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            # temperature=0.7,
            response_format=TaskGroup,
        )
    except Exception as e:
        print(e)
        return []

    tasks = completion.choices[0].message.parsed

    list_items = []
    for index, task in enumerate(tasks.tasks):
        processed_task = process_task(task, index, current_topic.id, db)
        list_items.append(processed_task)

    with open(f"data/tasks/topic_{topic_id}_tasks.json", "w") as file:
        json.dump(list_items, file, indent=4)

    rebuild_task_links(current_lesson.id)

    if should_close:
        db.close()

    return list_items


async def generate_adaptive_task(
    user_id: int, failed_task_id: int, user_solution: str, topic_id: int, error_analysis: dict = None, db=None
) -> Optional[int]:
    """
    Generate an adaptive task to address specific learning gaps.

    Args:
        user_id: ID of the user who needs the adaptive task
        failed_task_id: ID of the task the user failed
        user_solution: The incorrect solution submitted by the user
        topic_id: ID of the topic for the adaptive task
        error_analysis: Optional analysis of what went wrong
        db: Database session

    Returns:
        ID of the generated task, or None if generation failed
    """
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False

    try:
        # Get the original task details
        original_task = db.query(DBTask).filter(DBTask.id == failed_task_id).first()
        if not original_task:
            logger.error(f"Original task {failed_task_id} not found")
            return None

        # Get topic, lesson, and course context
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            logger.error(f"Topic {topic_id} not found")
            return None

        lesson = db.query(Lesson).filter(Lesson.id == topic.lesson_id).first()
        from models import Course

        course = db.query(Course).filter(Course.id == lesson.course_id).first()

        # Analyze the error and create targeted prompt
        error_context = _analyze_user_error(original_task, user_solution, error_analysis)

        # Get language instruction for adaptive tasks
        language_instruction = get_language_instruction(course.language if course else "English")

        # Create AI prompt for adaptive task generation
        system_prompt = f"""
        {language_instruction}
        
        You are an expert programming educator creating personalized remedial tasks.
        
        A student failed a task and needs a targeted practice exercise to address their specific learning gap.
        
        **Original Task Context:**
        - Task Name: {original_task.task_name}
        - Task Type: {original_task.type}
        - Topic: {topic.title} 
        - Concepts: {topic.concepts}
        
        **Student's Learning Gap:**
        {error_context}
        
        **Instructions:**
        Create ONE focused task that:
        1. Addresses the specific error pattern shown
        2. Is slightly simpler than the original to build confidence
        3. Reinforces the fundamental concept the student missed
        4. Provides a stepping stone toward mastering the original concept
        5. Uses engaging, relatable examples from Digital Humanities context
        
        **Task Requirements:**
        - Must be directly related to the missed concept
        - Should be completable in 5-10 minutes
        - Include clear guidance without giving away the answer
        - Match the original task type when possible
        """

        user_prompt = f"""
        Generate an adaptive task based on this failed attempt:
        
        **Original Task Data:** {original_task.data}
        **Student's Incorrect Solution:** {user_solution}
        **Error Pattern:** {error_context}
        
        Create a task that helps the student understand what they got wrong and practice the correct approach.
        """

        # Generate the adaptive task using OpenAI
        completion = client.beta.chat.completions.parse(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,  # Lower temperature for more focused remediation
            response_format=AdaptiveTask,
        )

        adaptive_task_data = completion.choices[0].message.parsed

        # Get the highest order number for tasks in this topic
        max_order = db.query(func.max(DBTask.order)).filter(DBTask.topic_id == topic_id).scalar() or 0

        # Create the new adaptive task
        new_task = task_model_mapping.get(type_mapping.get(adaptive_task_data.type.value, "UnknownType"), DBTask)(
            task_name=f"📝 {adaptive_task_data.name}",  # Mark as adaptive with emoji
            task_link=f"adaptive-{failed_task_id}-{user_id}",  # Unique identifier
            points=adaptive_task_data.points,
            order=max_order + 1,  # Add to end of topic
            topic_id=topic_id,
            data=_prepare_adaptive_task_data(adaptive_task_data),
            is_active=True,
            is_generated=True,
            generated_for_user_id=user_id,
            source_task_id=failed_task_id,
            generation_prompt=system_prompt + "\n\n" + user_prompt,
            ai_model_used="gpt-5",
        )

        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        logger.info(f"Generated adaptive task {new_task.id} for user {user_id} based on failed task {failed_task_id}")

        return new_task.id

    except Exception as e:
        logger.error(f"Failed to generate adaptive task: {str(e)}")
        db.rollback()
        return None
    finally:
        if should_close:
            db.close()


def _analyze_user_error(original_task: DBTask, user_solution: str, error_analysis: dict = None) -> str:
    """Analyze what went wrong with the user's solution"""
    analysis_parts = []

    # Add task type context
    if original_task.type == "code":
        analysis_parts.append(f"This was a coding task. The student's code was: {user_solution}")
    elif "quiz" in original_task.type.lower():
        analysis_parts.append(f"This was a quiz question. The student's answer was: {user_solution}")

    # Add any provided error analysis
    if error_analysis:
        if "syntax_errors" in error_analysis:
            analysis_parts.append(f"Syntax errors detected: {error_analysis['syntax_errors']}")
        if "logic_errors" in error_analysis:
            analysis_parts.append(f"Logic issues: {error_analysis['logic_errors']}")
        if "concept_gaps" in error_analysis:
            analysis_parts.append(f"Concept understanding gaps: {error_analysis['concept_gaps']}")

    return " ".join(analysis_parts)


def _prepare_adaptive_task_data(adaptive_task: AdaptiveTask) -> dict:
    """Convert AdaptiveTask to the data format expected by the Task model"""
    data = {}

    if adaptive_task.type.value == "code":
        data["text"] = adaptive_task.question
        if adaptive_task.explanation:
            data["text"] += f"\n\n💡 **Tip:** {adaptive_task.explanation}"
        data["code"] = adaptive_task.code or "# Your code here..."

    elif adaptive_task.type.value == "multiple_choice":
        data["question"] = adaptive_task.question
        if adaptive_task.explanation:
            data["question"] += f"\n\n💡 **Note:** {adaptive_task.explanation}"
        # For now, generate simple options - can be enhanced later
        data["options"] = [
            {"id": "1", "name": "Option A"},
            {"id": "2", "name": "Option B"},
            {"id": "3", "name": "Option C"},
            {"id": "4", "name": "Option D"},
        ]
        data["correctAnswers"] = ["1"]  # Default to first option

    elif adaptive_task.type.value == "single_question":
        data["question"] = adaptive_task.question
        if adaptive_task.explanation:
            data["question"] += f"\n\n💡 **Guidance:** {adaptive_task.explanation}"

    return data


# generate_tasks(19, 5)
