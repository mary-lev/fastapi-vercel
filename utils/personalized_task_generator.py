"""
Personalized Task Generation Utilities

Provides analysis of student struggles and generates personalized review tasks.
"""

import json
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from models import (
    StudentLessonAnalysis, StudentTaskAnalysis,
    Task, Topic, Course, User, TaskAttempt
)
from utils.learning_analytics import get_openai_client, LLM_MODEL_NAME
from utils.task_generator import process_task, get_language_instruction
from utils.structured_logging import get_logger

logger = get_logger("personalized_tasks")


def _calculate_confidence(lesson_analyses: List, task_analyses: List) -> str:
    """
    Calculate confidence level in the analysis based on data quantity/quality.

    Returns:
        "high", "medium", or "low"
    """
    if len(lesson_analyses) >= 5 and len(task_analyses) >= 30:
        return "high"
    elif len(lesson_analyses) >= 3 and len(task_analyses) >= 15:
        return "medium"
    else:
        return "low"


async def synthesize_student_struggles(
    user_id: int,
    course_id: int,
    db: Session
) -> Optional[Dict]:
    """
    Aggregate lesson analyses to find 3-4 critical concept gaps.

    Args:
        user_id: Student ID
        course_id: Course ID
        db: Database session

    Returns:
        Dictionary with critical_concepts, analysis_summary, difficulty_level, confidence
        or None if insufficient data
    """
    # 1. Get all lesson analyses for this student
    lesson_analyses = db.query(StudentLessonAnalysis).filter(
        StudentLessonAnalysis.user_id == user_id,
        StudentLessonAnalysis.course_id == course_id
    ).all()

    if not lesson_analyses:
        logger.warning(f"No lesson analyses found for user {user_id} in course {course_id}")
        return None

    # 2. Extract struggling concepts from each lesson
    all_struggles = {}  # concept -> {count, lessons, severity}

    for la in lesson_analyses:
        struggling = la.analysis.get('struggling_concepts', [])
        pacing = la.analysis.get('pacing', 'appropriate')

        for concept in struggling:
            if concept not in all_struggles:
                all_struggles[concept] = {
                    'count': 0,
                    'lessons': [],
                    'severity': 0
                }

            all_struggles[concept]['count'] += 1
            all_struggles[concept]['lessons'].append(la.lesson_id)

            # Weight by pacing (overwhelmed = higher priority)
            if pacing == 'overwhelmed':
                all_struggles[concept]['severity'] += 2
            else:
                all_struggles[concept]['severity'] += 1

    # 3. Get task-level details for context
    task_analyses = db.query(StudentTaskAnalysis).filter(
        StudentTaskAnalysis.user_id == user_id,
        StudentTaskAnalysis.course_id == course_id
    ).all()

    persistent_difficulty_count = len([
        ta for ta in task_analyses
        if ta.analysis.get('learning_progression') == 'persistent_difficulty'
    ])

    # Calculate completion rate
    completion_rate = sum(la.completion_percentage for la in lesson_analyses) / len(lesson_analyses)

    # 4. Use LLM to synthesize top 3-4 critical gaps
    client = get_openai_client()

    prompt = f"""Analyze this student's learning struggles across course lessons:

STRUGGLING CONCEPTS (frequency, severity):
{json.dumps(all_struggles, indent=2, ensure_ascii=False)}

LEARNING PATTERNS:
- Total lessons analyzed: {len(lesson_analyses)}
- Tasks with persistent difficulty: {persistent_difficulty_count}
- Completion rate: {completion_rate:.1f}%

TASK: Identify 3-4 MOST CRITICAL concepts for remediation.

PRIORITIZATION CRITERIA:
1. Concepts appearing in multiple lessons (cross-lesson persistence)
2. Foundational concepts blocking advanced topics
3. Recent struggles (recency bias)
4. High severity score (overwhelmed pacing)

Return JSON:
{{
    "critical_concepts": [
        "Concept 1 in Russian",
        "Concept 2 in Russian",
        "Concept 3 in Russian"
    ],
    "rationale": "Brief explanation of why these 3 were chosen",
    "difficulty_level": "beginner|intermediate|advanced"
}}

Use Russian for concept names. Be specific (not "циклы" but "вложенные циклы с enumerate").
"""

    from schemas.personalized_tasks import StudentStruggleAnalysisSchema

    try:
        response = client.beta.chat.completions.parse(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an expert programming educator analyzing student learning patterns."},
                {"role": "user", "content": prompt}
            ],
            response_format=StudentStruggleAnalysisSchema
        )

        result = response.choices[0].message.parsed

        if not result:
            logger.error(f"Failed to parse LLM response for user {user_id}")
            return None

        return {
            "user_id": user_id,
            "critical_concepts": result.critical_concepts,
            "analysis_summary": result.rationale,
            "difficulty_level": result.difficulty_level,
            "lesson_ids_analyzed": [la.lesson_id for la in lesson_analyses],
            "confidence": _calculate_confidence(lesson_analyses, task_analyses)
        }

    except Exception as e:
        logger.error(f"Error in synthesize_student_struggles for user {user_id}: {str(e)}")
        return None


def _get_difficult_tasks_context(user_id: int, course_id: int, db: Session, limit: int = 5) -> str:
    """
    Get context about the student's most difficult tasks with error patterns.

    Returns formatted string with task details, attempts, and common errors.
    """
    # Get task analyses with multiple failed attempts or no success
    difficult_analyses = db.query(StudentTaskAnalysis).filter(
        StudentTaskAnalysis.user_id == user_id,
        StudentTaskAnalysis.course_id == course_id,
        StudentTaskAnalysis.failed_attempts > 0  # Has failed at least once
    ).order_by(
        StudentTaskAnalysis.failed_attempts.desc(),  # Most failures first
        StudentTaskAnalysis.last_attempt_at.desc()   # Most recent
    ).limit(limit).all()

    if not difficult_analyses:
        return "No specific difficult tasks identified yet."

    context_parts = []
    for analysis in difficult_analyses:
        task = db.query(Task).filter(Task.id == analysis.task_id).first()
        if not task:
            continue

        error_patterns = analysis.analysis.get('error_patterns', [])
        attempts_count = analysis.total_attempts
        time_spent = analysis.total_time_spent or 'unknown'
        success_status = "✅ Eventually solved" if analysis.final_success else "❌ Still unsolved"

        task_info = f"""
Task: {task.task_name}
Type: {task.type}
Status: {success_status}
Attempts: {attempts_count} (failed: {analysis.failed_attempts}, successful: {analysis.successful_attempts})
Time spent: {time_spent}
Error patterns: {', '.join(error_patterns) if error_patterns else 'Not analyzed'}
Learning progression: {analysis.analysis.get('learning_progression', 'unknown')}
"""
        context_parts.append(task_info.strip())

    return "\n\n".join(context_parts)


def _calculate_optimal_task_count(struggle_analysis: Dict, task_analyses: List) -> int:
    """
    Calculate optimal number of tasks based on struggle severity.

    Returns number between 4 and 10.
    """
    num_concepts = len(struggle_analysis.get('critical_concepts', []))
    difficulty = struggle_analysis.get('difficulty_level', 'intermediate')
    confidence = struggle_analysis.get('confidence', 'low')

    # Base calculation: 1-2 tasks per concept
    base_tasks = min(num_concepts * 2, 10)

    # Adjust based on difficulty and confidence
    if difficulty == 'beginner' and confidence == 'low':
        # More practice needed for beginners with low confidence
        return min(base_tasks + 2, 10)
    elif difficulty == 'advanced' or confidence == 'high':
        # Fewer but more challenging tasks for advanced students
        return max(base_tasks - 2, 4)
    else:
        # Default range
        return max(min(base_tasks, 10), 4)


def _get_topic_content(topic: Topic) -> str:
    """
    Get topic content from file if available.

    Returns topic content or fallback description.
    """
    if not topic.content_file_md:
        return f"Topic: {topic.title}\n\nConcepts: {topic.concepts or 'Not specified'}"

    try:
        content_path = topic.content_file_md
        # Try different path variations
        if content_path.startswith("/"):
            with open(content_path, "r") as f:
                return f.read()
        elif content_path.startswith("data/"):
            with open(content_path, "r") as f:
                return f.read()
        else:
            # Try common base directories
            for base_dir in ["data/textbook/", "data/tasks-2025/"]:
                try:
                    with open(f"{base_dir}{content_path}", "r") as f:
                        return f.read()
                except FileNotFoundError:
                    continue
    except Exception as e:
        logger.warning(f"Failed to read topic content for {topic.id}: {str(e)}")

    # Fallback
    return f"Topic: {topic.title}\n\nConcepts: {topic.concepts or 'Not specified'}\n\nObjectives: {topic.objectives or 'Not specified'}"


def _generate_task_breakdown(num_tasks: int, concepts: List[str]) -> str:
    """
    Generate a task breakdown based on number of tasks and concepts.

    Returns formatted string showing suggested task progression.
    """
    if num_tasks <= 4:
        return f"""- Task 1: Basic practice of {concepts[0] if concepts else 'first concept'} (easy)
- Task 2: Application of {concepts[1] if len(concepts) > 1 else 'second concept'} (medium)
- Task 3: Combined practice (medium-hard)
- Task 4: Integration challenge (combines all concepts)"""

    elif num_tasks <= 6:
        return f"""- Tasks 1-2: Basic reinforcement of individual concepts (easy)
- Tasks 3-4: Progressive application (medium)
- Task 5: Combined concepts (medium-hard)
- Task 6: Integration challenge (hard)"""

    else:  # 7-10 tasks
        return f"""- Tasks 1-3: Individual concept practice (easy to medium)
- Tasks 4-6: Progressive application and combinations (medium)
- Tasks {num_tasks-2}-{num_tasks-1}: Complex applications (medium-hard)
- Task {num_tasks}: Final integration challenge (combines all concepts)"""


def generate_personalized_tasks(
    topic_id: int,
    user_id: int,
    struggle_analysis: Dict,
    course: Course,
    db: Session,
    num_tasks: int = None  # Now optional, will be calculated if not provided
) -> List[int]:
    """
    Generate personalized practice tasks addressing specific concept gaps.

    Args:
        topic_id: Personal topic ID (e.g., Topic 54)
        user_id: Student ID
        struggle_analysis: Output from synthesize_student_struggles()
        course: Course object for language context
        db: Database session
        num_tasks: Number of tasks to generate (if None, will be calculated dynamically)

    Returns:
        List of generated task IDs
    """
    critical_concepts = struggle_analysis['critical_concepts']
    difficulty = struggle_analysis['difficulty_level']

    # Get topic for context
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        logger.error(f"Topic {topic_id} not found")
        return []

    # Calculate optimal number of tasks if not provided
    task_analyses = db.query(StudentTaskAnalysis).filter(
        StudentTaskAnalysis.user_id == user_id,
        StudentTaskAnalysis.course_id == course.id
    ).all()

    if num_tasks is None:
        num_tasks = _calculate_optimal_task_count(struggle_analysis, task_analyses)
        logger.info(f"Calculated optimal task count: {num_tasks} tasks for user {user_id}")

    # Get context about difficult tasks
    difficult_tasks_context = _get_difficult_tasks_context(user_id, course.id, db)

    # Get topic content
    topic_content = _get_topic_content(topic)

    # Build enhanced personalized prompt
    custom_instructions = f"""
PERSONALIZED REVIEW FOR STUDENT {user_id}

STUDENT LEARNING PROFILE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Struggling concepts:
{chr(10).join(f"  • {concept}" for concept in critical_concepts)}

Overall level: {difficulty}
Analysis: {struggle_analysis['analysis_summary']}
Confidence in analysis: {struggle_analysis.get('confidence', 'medium')}

MOST DIFFICULT TASKS FOR THIS STUDENT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{difficult_tasks_context}

⚠️  CRITICAL: DO NOT RECREATE THESE EXACT TASKS!
The tasks above show what the student struggled with and eventually solved.
Your job is to create NEW tasks that:
- Target the SAME error patterns and concepts
- Use DIFFERENT scenarios, contexts, and examples
- Are fresh challenges, not just variations of what they already completed
- Build on their learning without boring repetition

DESIGN PRINCIPLES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Each task targets 1-2 struggling concepts - design problems that expose those same error patterns
2. Start slightly easier than failed attempts, gradually increase complexity
3. Final task: integrative challenge combining 2-3 concepts
4. Use Digital Humanities contexts: literary texts, corpora, manuscripts, bibliographic data

DIFFICULTY PROGRESSION ({num_tasks} tasks):
{_generate_task_breakdown(num_tasks, critical_concepts)}

CODE FIELD INSTRUCTIONS (CRITICAL):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  NEVER use input() function - provide test data in variables!
⚠️  The 'code' field must contain starter/buggy code, NEVER complete solutions!

Task types and code requirements:

1. DEBUGGING tasks (40% of tasks):
   - Provide code with subtle bugs matching student's error patterns
   - Bugs should be realistic: wrong method (lstrip vs strip), list mutation during iteration, off-by-one errors
   - Minimal comments - let students discover issues through testing
   - Example comment style: # TODO: проверьте результат

2. COMPLETION tasks (30% of tasks):
   - Provide skeleton code with TODOs
   - Minimal guidance - students should apply learned concepts
   - Example: # TODO: обработайте пустые строки

3. MODIFICATION tasks (30% of tasks):
   - Provide working code that needs extension
   - Brief task description only
   - Students figure out what to change

TASK DESCRIPTION GUIDELINES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ State WHAT needs to be done, not HOW to do it
✓ No "НЕЛЬЗЯ" (forbidden) lists - let students discover constraints
✓ No "Разрешено" (allowed) lists - students should know solutions from lessons
✓ Brief, focused descriptions (2-3 sentences max)
✓ Let students figure out the approach themselves
✓ Task difficulty comes from problem-solving, not following instructions

Example of TOO MUCH guidance (avoid):
❌ "Нельзя использовать pop()/remove() и нельзя модифицировать список во время for-итерации. Разрешено: while с индексом"

Example of RIGHT level (use):
✅ "Удалите пустые элементы из списка tokens. Код работает неправильно - найдите и исправьте ошибку."
"""

    # Generate tasks using OpenAI
    client = get_openai_client()

    system_prompt = f"""
{get_language_instruction(course.language)}

You are an expert programming educator specializing in personalized remedial instruction for graduate students in Digital Humanities programs.
You understand learning science and know how to scaffold difficult concepts for struggling students.

CONTEXT:
We are creating a personalized set of tasks for a graduate student in the Digital Humanities program learning their first Python course.
Create tasks that help this specific student overcome their documented struggles and rebuild confidence, following this specific structure:

{custom_instructions}
"""

    user_prompt = f"""
Generate {num_tasks} personalized code tasks targeting: {', '.join(critical_concepts)}

TOPIC CONTEXT:
Topic: {topic.title} - {topic.objectives or 'Practice and consolidate course concepts'}

RELEVANT CONTENT (for alignment with taught material):
{topic_content[:800]}...

KEY REQUIREMENTS:
✓ Practice learned concepts, not teach new ones - students should already know the solutions
✓ Progressive difficulty: easy → medium → hard across the {num_tasks} tasks
✓ Diverse scenarios: different DH examples (authors, manuscripts, corpora, etc.)
✓ Mix task types: 40% debugging, 30% completion, 30% modification
"""

    from utils.task_generator import TaskGroup

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=TaskGroup
        )

        tasks = response.choices[0].message.parsed

        # Process and save tasks
        task_ids = []

        # Get current max order in this topic
        from sqlalchemy import func
        max_order = db.query(func.max(Task.order)).filter(Task.topic_id == topic_id).scalar() or 0

        for index, task in enumerate(tasks.tasks):
            # Add personalization markers (just emoji, no text prefix)
            task_name = f"📝 {task.task_name}"

            # Process task using existing function (adds to DB)
            process_task(task, index + max_order, topic_id, db)

            # Get the just-created task
            new_task = db.query(Task).filter(
                Task.topic_id == topic_id
            ).order_by(Task.id.desc()).first()

            # Update with personalization fields
            new_task.task_name = task_name
            new_task.is_generated = True
            new_task.generated_for_user_id = user_id
            new_task.generation_prompt = system_prompt + "\n\n" + user_prompt
            new_task.ai_model_used = "gpt-5"
            new_task.is_active = True
            new_task.task_link = f"{topic_id}-personal-{user_id}-{index+1}"

            # Store which concept this addresses
            if not new_task.data:
                new_task.data = {}
            new_task.data['_addressed_concept'] = critical_concepts[min(index, len(critical_concepts)-1)]

            db.commit()
            db.refresh(new_task)

            task_ids.append(new_task.id)

        logger.info(
            f"Generated {len(task_ids)} personalized tasks for user {user_id}",
            extra={
                "user_id": user_id,
                "topic_id": topic_id,
                "concepts": critical_concepts,
                "task_ids": task_ids
            }
        )

        return task_ids

    except Exception as e:
        logger.error(f"Error generating personalized tasks for user {user_id}: {str(e)}")
        return []
