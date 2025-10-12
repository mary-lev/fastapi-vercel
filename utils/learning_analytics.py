"""
Learning Analytics Utility Functions

Provides time gap analysis, LLM prompt generation, and student performance analysis
for the three-tier learning analytics system (task → lesson → course).
"""

import json
from datetime import timedelta, datetime
from typing import List, Dict, Any, Optional
from functools import lru_cache
from sqlalchemy.orm import Session

from models import (
    Task, TaskAttempt, User, Lesson, Course, Topic,
    StudentTaskAnalysis, StudentLessonAnalysis, StudentCourseProfile
)


# ===============================================================================
# Configuration Constants
# ===============================================================================

# Default LLM model for all analytics
LLM_MODEL_NAME = "gpt-5"


# ===============================================================================
# OpenAI Client Singleton
# ===============================================================================

@lru_cache(maxsize=1)
def get_openai_client():
    """
    Get singleton OpenAI client instance.

    Uses lru_cache to ensure only one client is created and reused across all
    analytics functions, reducing overhead and connection setup time.

    Returns:
        OpenAI client instance configured with API key from settings
    """
    import openai
    from config import settings
    return openai.OpenAI(api_key=settings.OPENAI_API_KEY)


# ===============================================================================
# Time Gap Conversion Functions
# ===============================================================================


def calculate_time_gaps(attempts: List[TaskAttempt]) -> Dict[str, Any]:
    """
    Convert attempt timestamps into human-readable time gaps for LLM understanding.

    Args:
        attempts: List of TaskAttempt objects sorted by submitted_at

    Returns:
        Dictionary with:
        - attempt_time_gaps: List of human-readable time gaps between attempts
        - total_time_spent: Human-readable total duration

    Example:
        {
            "attempt_time_gaps": ["Immediately", "After 5 minutes", "One day later"],
            "total_time_spent": "3 hours across 2 days"
        }
    """
    if len(attempts) <= 1:
        return {
            "attempt_time_gaps": ["Single attempt"],
            "total_time_spent": "Single attempt"
        }

    gaps = []
    sorted_attempts = sorted(attempts, key=lambda a: a.submitted_at)

    for i in range(1, len(sorted_attempts)):
        delta = sorted_attempts[i].submitted_at - sorted_attempts[i-1].submitted_at
        gaps.append(_humanize_timedelta(delta))

    # Total time calculation
    first = sorted_attempts[0].submitted_at
    last = sorted_attempts[-1].submitted_at
    total_delta = last - first

    return {
        "attempt_time_gaps": gaps,
        "total_time_spent": _humanize_duration(total_delta, len(sorted_attempts))
    }


def _humanize_timedelta(delta: timedelta) -> str:
    """
    Convert timedelta to human text like 'After 5 minutes' or 'One day later'.

    Args:
        delta: Time difference between two attempts

    Returns:
        Human-readable string describing the time gap
    """
    seconds = delta.total_seconds()

    if seconds < 60:
        return "Immediately"
    elif seconds < 300:  # 5 minutes
        mins = int(seconds / 60)
        return f"After {mins} minute{'s' if mins > 1 else ''}"
    elif seconds < 3600:  # 1 hour
        mins = int(seconds / 60)
        return f"After {mins} minutes"
    elif seconds < 7200:  # 2 hours
        return "After about an hour"
    elif seconds < 86400:  # 1 day
        hours = int(seconds / 3600)
        return f"After {hours} hour{'s' if hours > 1 else ''}"
    elif seconds < 172800:  # 2 days
        return "One day later"
    else:
        days = int(seconds / 86400)
        return f"After {days} days"


def _humanize_duration(delta: timedelta, attempt_count: int) -> str:
    """
    Convert total duration to text like '3 hours across 2 days'.

    Args:
        delta: Total time from first to last attempt
        attempt_count: Number of attempts made

    Returns:
        Human-readable string describing total time spent
    """
    total_seconds = delta.total_seconds()

    if total_seconds < 3600:  # < 1 hour
        mins = int(total_seconds / 60)
        return f"{mins} minute{'s' if mins != 1 else ''}"
    elif total_seconds < 86400:  # < 1 day
        hours = int(total_seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''}"
    else:
        days = int(total_seconds / 86400)
        hours = int((total_seconds % 86400) / 3600)
        if attempt_count > 1:
            if hours > 0:
                return f"{hours} hour{'s' if hours != 1 else ''} across {days} day{'s' if days != 1 else ''}"
            else:
                return f"{days} day{'s' if days != 1 else ''}"
        else:
            return f"{days} day{'s' if days != 1 else ''}"


# ===============================================================================
# Attempt Formatting for LLM
# ===============================================================================


def _format_attempts_for_llm(attempts: List[TaskAttempt], max_show: int = 20) -> str:
    """
    Format task attempts for LLM analysis, handling outliers by condensing.

    For outliers (>max_show attempts), shows first 5 + last 15 to capture
    the learning progression without overwhelming the context window.

    Args:
        attempts: List of TaskAttempt objects
        max_show: Maximum attempts to show in full before condensing

    Returns:
        Formatted string with attempt history for LLM
    """
    if len(attempts) <= max_show:
        # Show all attempts
        formatted_attempts = []
        for i, attempt in enumerate(attempts):
            status = "SUCCESS" if attempt.is_successful else "FAILED"
            code_preview = attempt.attempt_content[:500] if attempt.attempt_content else "[No code]"

            # Get AI feedback if available
            feedback_preview = ""
            if hasattr(attempt, 'ai_feedback') and attempt.ai_feedback:
                feedback = attempt.ai_feedback[0].feedback[:200]
                feedback_preview = f"Feedback: {feedback}...\n"

            formatted_attempts.append(
                f"Attempt {i+1}: {status}\n"
                f"Code:\n{code_preview}...\n"
                f"{feedback_preview}"
            )
        return "\n".join(formatted_attempts)
    else:
        # Outlier case: show first 5 + last 15
        first_five = attempts[:5]
        last_fifteen = attempts[-15:]

        formatted = "FIRST 5 ATTEMPTS:\n"
        for i, attempt in enumerate(first_five):
            status = "SUCCESS" if attempt.is_successful else "FAILED"
            code_preview = attempt.attempt_content[:300] if attempt.attempt_content else "[No code]"
            formatted += f"Attempt {i+1}: {status}\nCode: {code_preview}...\n\n"

        formatted += f"\n... [{len(attempts) - 20} attempts omitted] ...\n\n"

        formatted += "LAST 15 ATTEMPTS:\n"
        for i, attempt in enumerate(last_fifteen):
            status = "SUCCESS" if attempt.is_successful else "FAILED"
            code_preview = attempt.attempt_content[:300] if attempt.attempt_content else "[No code]"
            formatted += f"Attempt {len(attempts)-15+i+1}: {status}\nCode: {code_preview}...\n\n"

        return formatted


# ===============================================================================
# Task-Level Analysis Prompt Generation
# ===============================================================================


def generate_task_analysis_prompt(
    user: User,
    task: Task,
    attempts: List[TaskAttempt],
    course: Course
) -> Dict[str, str]:
    """
    Generate LLM prompt for task-level student analysis.

    Args:
        user: User object
        task: Task object being analyzed
        attempts: All attempts by the user on this task
        course: Course object for context

    Returns:
        Dictionary with 'system' and 'user' prompts
    """
    time_data = calculate_time_gaps(attempts)

    # Extract comprehensive task information from data JSON
    task_info = []

    if isinstance(task.data, dict):
        # Task description/instructions (handle both 'text' and 'description' field names)
        description = task.data.get('text') or task.data.get('description', '')
        if description:
            task_info.append(f"TASK INSTRUCTIONS:\n{description}")

        # Task requirements/objectives
        requirements = task.data.get('requirements', [])
        if requirements:
            task_info.append("REQUIREMENTS:\n" + "\n".join(f"- {req}" for req in requirements))

        # Starter code/template (handle 'code', 'starter_code', 'template', 'code_template')
        starter_code = (
            task.data.get('code') or
            task.data.get('starter_code') or
            task.data.get('template') or
            task.data.get('code_template')
        )
        if starter_code:
            # Clean up if it's just a placeholder
            if starter_code and not starter_code.strip().startswith('#'):
                task_info.append(f"STARTER CODE PROVIDED:\n{starter_code}")
            elif starter_code and len(starter_code.strip()) > 20:  # More than just "# Your code here"
                task_info.append(f"STARTER CODE PROVIDED:\n{starter_code}")

        # Correct answer (for reference - helps LLM understand what's expected)
        correct_answer = task.data.get('correct_answer')
        if correct_answer and correct_answer != starter_code:
            # Only show first 200 chars to give context without spoiling
            preview = correct_answer[:200] + "..." if len(correct_answer) > 200 else correct_answer
            task_info.append(f"EXPECTED SOLUTION PATTERN (reference):\n{preview}")

        # Expected output/behavior
        expected_output = task.data.get('expected_output') or task.data.get('expected_behavior')
        if expected_output:
            task_info.append(f"EXPECTED OUTPUT:\n{expected_output}")

        # Test cases (if visible to student)
        test_cases = task.data.get('test_cases', [])
        if test_cases and len(test_cases) > 0:
            # Show first 2-3 test cases as examples
            visible_tests = test_cases[:3]
            test_desc = "\n".join([
                f"- Input: {tc.get('input', 'N/A')} → Expected: {tc.get('expected', 'N/A')}"
                for tc in visible_tests if isinstance(tc, dict)
            ])
            if test_desc:
                task_info.append(f"TEST CASES (sample):\n{test_desc}")

        # Hints or learning objectives
        hints = task.data.get('hints', [])
        if hints:
            task_info.append("HINTS PROVIDED:\n" + "\n".join(f"- {hint}" for hint in hints[:3]))

        learning_objectives = task.data.get('learning_objectives', [])
        if learning_objectives:
            task_info.append("LEARNING OBJECTIVES:\n" + "\n".join(f"- {obj}" for obj in learning_objectives))

    task_details = "\n\n".join(task_info) if task_info else "No detailed task information available"

    system_prompt = f"""You are an expert programming educator analyzing a student's learning patterns in a {course.language or 'Python'} programming course.

Analyze the student's task attempts to identify:
1. What knowledge/skill this task tests and trains (one-line summary)
2. Error patterns and misconceptions
3. Learning progression (struggle → breakthrough vs smooth)
4. Concept gaps that need reinforcement
5. Strengths demonstrated
6. Whether difficulty level is appropriate

Provide structured analysis focusing on actionable insights for personalized learning.
Be specific and reference actual code patterns when possible."""

    user_prompt = f"""STUDENT: {user.username} (ID: {user.id})
COURSE: {course.title}

TASK: {task.task_name}
TASK TYPE: {task.type}
POINTS: {task.points}

TASK DETAILS:
{task_details}

STUDENT ATTEMPTS: {len(attempts)} total
- Successful: {len([a for a in attempts if a.is_successful])}
- Failed: {len([a for a in attempts if not a.is_successful])}

TIME PATTERN:
- Total time: {time_data['total_time_spent']}
- Time gaps between attempts: {', '.join(time_data['attempt_time_gaps'])}

ATTEMPT HISTORY:
{_format_attempts_for_llm(attempts, max_show=20)}

ANALYSIS REQUIREMENTS:
1. task_summary: One-line summary of what knowledge/skill this task tests and trains (e.g., "Tests dictionary comprehension and .get() idiom for word frequency counting")
2. error_patterns: List 2-3 specific error patterns (e.g., "off-by-one errors in loop range", "confusion between append() and extend()")
3. learning_progression: Classify as ONE of: "immediate_success", "struggle_then_breakthrough", "persistent_difficulty"
4. concept_gaps: List 2-3 specific concept gaps if any (be precise: "list comprehension syntax" not just "loops")
5. strengths: Note 1-2 demonstrated strengths (e.g., "good variable naming", "proper edge case handling")
6. help_needed: Boolean - true if student needs instructor intervention (same error repeated 3+ times)
7. difficulty_level: Assess as ONE of: "too_easy", "appropriate", "too_hard"

Respond in JSON format with exactly these keys: task_summary, error_patterns, learning_progression, concept_gaps, strengths, help_needed, difficulty_level"""

    return {
        "system": system_prompt,
        "user": user_prompt
    }


# ===============================================================================
# Lesson-Level Analysis Prompt Generation
# ===============================================================================


def generate_lesson_analysis_prompt(
    user: User,
    lesson: Lesson,
    course: Course,
    task_analyses: List[StudentTaskAnalysis]
) -> Dict[str, str]:
    """
    Generate LLM prompt for lesson-level synthesis.

    Args:
        user: User object
        lesson: Lesson object being analyzed
        course: Course object for context
        task_analyses: All StudentTaskAnalysis objects for tasks in this lesson

    Returns:
        Dictionary with 'system' and 'user' prompts
    """
    # Format task analyses for LLM
    formatted_tasks = []
    for ta in task_analyses:
        task = ta.task
        formatted_tasks.append(f"""
Task: {task.task_name} ({task.points} points)
Attempts: {ta.total_attempts} (Success: {ta.final_success})
Time: {ta.total_time_spent}
Analysis:
  - Learning progression: {ta.analysis.get('learning_progression', 'N/A')}
  - Concept gaps: {', '.join(ta.analysis.get('concept_gaps', []))}
  - Strengths: {', '.join(ta.analysis.get('strengths', []))}
""")

    system_prompt = f"""You are an expert programming educator synthesizing a student's lesson-level progress in a {course.language or 'Python'} course.

Analyze patterns across multiple tasks to identify:
1. Concepts mastered vs struggling
2. Learning pace (too fast/slow/appropriate)
3. Retention across topics
4. Help-seeking patterns
5. Topic dependency issues

Provide actionable insights for lesson design and student support."""

    user_prompt = f"""STUDENT: {user.username} (ID: {user.id})
COURSE: {course.title}
LESSON: {lesson.title}

LESSON DESCRIPTION: {lesson.description}
TOTAL TOPICS: {len(lesson.topics)}
TOTAL TASKS ANALYZED: {len(task_analyses)}

TASK-LEVEL SUMMARIES:
{''.join(formatted_tasks)}

ANALYSIS REQUIREMENTS:
1. mastered_concepts: List 2-4 concepts that appeared as strengths across multiple tasks
2. struggling_concepts: List 2-4 concepts that appeared as gaps across multiple tasks
3. pacing: Assess as ONE of: "too_fast" (student overwhelmed), "appropriate", "too_slow" (student bored)
4. retention_score: Float 0.0-1.0 indicating how well concepts from early tasks were retained in later tasks
5. help_seeking_pattern: Assess as ONE of: "too_frequent" (excessive retries without learning), "appropriate", "too_rare" (gives up too easily)
6. topic_dependencies_issues: List any cases where weak foundation in earlier topic caused issues in later topic

Respond in JSON format with exactly these keys: mastered_concepts, struggling_concepts, pacing, retention_score, help_seeking_pattern, topic_dependencies_issues"""

    return {
        "system": system_prompt,
        "user": user_prompt
    }


# ===============================================================================
# Student Summary Generation (Lesson & Course Levels)
# ===============================================================================


def generate_lesson_student_summary_prompt(analysis_data: dict, lesson_title: str) -> str:
    """
    Generate prompt to create motivational lesson summary for students.

    Args:
        analysis_data: The JSON analysis from lesson-level LLM call
        lesson_title: Title of the lesson

    Returns:
        Prompt string for generating student-friendly summary
    """
    return f"""Based on this technical analysis of a student's progress in "{lesson_title}":

{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Write a brief (2-3 sentences), encouraging message for the student that:
- Acknowledges their effort and specific progress in this lesson
- Highlights 1-2 concepts they've mastered
- Offers constructive guidance if they struggled with something (frame positively)
- Uses motivational tone appropriate for learning programming

Avoid: technical jargon, mentioning "analysis", being overly critical
Focus on: growth mindset, specific achievements, readiness for next lesson

Example tone: "Great work on {lesson_title}! You've really mastered loops and conditionals, and your problem-solving approach is getting stronger. Keep practicing with nested structures – you're on the right track!"

Write ONLY the student message, no additional commentary."""


def generate_course_student_summary_prompt(analysis_data: dict, course_title: str) -> str:
    """
    Generate prompt to create congratulatory course summary for students.

    Args:
        analysis_data: The JSON analysis from course-level LLM call
        course_title: Title of the course

    Returns:
        Prompt string for generating congratulatory dashboard message
    """
    return f"""Based on this comprehensive analysis of a student's progress in "{course_title}":

{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Write a congratulatory message (3-4 sentences) for the student's dashboard that:
- Celebrates their course completion with specific achievements
- Highlights 2-3 core strengths they've developed
- Acknowledges growth areas and frames them as future opportunities
- Encourages continued learning with enthusiasm

Avoid: generic praise, mentioning "analysis", dwelling on weaknesses
Focus on: transformation, specific skills gained, readiness for advanced topics, pride in achievement

Example tone: "Congratulations on completing {course_title}! You've transformed from a beginner into a confident programmer with strong problem-solving and debugging skills. Your persistence through challenging topics like recursion really paid off. You're well-prepared for advanced programming – keep building amazing things!"

Write ONLY the congratulatory message, no additional commentary."""


# ===============================================================================
# Helper Functions
# ===============================================================================


def needs_lesson_analysis_update(
    existing_analysis: Optional[StudentLessonAnalysis],
    current_completion_percentage: float
) -> bool:
    """
    Determine if lesson analysis needs regeneration.

    Args:
        existing_analysis: Existing StudentLessonAnalysis or None
        current_completion_percentage: Current lesson completion %

    Returns:
        True if analysis should be regenerated
    """
    if not existing_analysis:
        return True

    # Regenerate if completion changed by >10%
    completion_delta = abs(
        float(existing_analysis.completion_percentage) - current_completion_percentage
    )
    return completion_delta > 10.0


def is_course_profile_outdated(
    profile: StudentCourseProfile,
    days_threshold: int = 7
) -> bool:
    """
    Check if course profile is outdated and needs regeneration.

    Args:
        profile: StudentCourseProfile object
        days_threshold: Number of days before considering outdated

    Returns:
        True if profile is older than threshold
    """
    if not profile:
        return True

    age = datetime.utcnow() - profile.analyzed_at
    return age.days > days_threshold


def get_course_from_task(task: Task, db: Session) -> Course:
    """
    Get course object from a task by traversing relationships.

    Args:
        task: Task object
        db: Database session

    Returns:
        Course object
    """
    topic = db.query(Topic).filter(Topic.id == task.topic_id).first()
    lesson = db.query(Lesson).filter(Lesson.id == topic.lesson_id).first()
    course = db.query(Course).filter(Course.id == lesson.course_id).first()
    return course


# ===============================================================================
# Analysis Execution Functions (with OpenAI Integration)
# ===============================================================================


async def analyze_task_performance(
    user_id: int,
    task_id: int,
    db: Session
) -> Optional[StudentTaskAnalysis]:
    """
    Analyze student's performance on a specific task using OpenAI.

    Creates or updates StudentTaskAnalysis record with:
    - Attempt statistics and time gaps
    - LLM-generated analysis (error patterns, strengths, etc.)
    - Professor notes for detailed technical assessment

    Args:
        user_id: User ID
        task_id: Task ID
        db: Database session

    Returns:
        StudentTaskAnalysis object or None if analysis failed
    """
    from schemas.learning_analytics import TaskAnalysisSchema

    # Get all attempts for this user and task
    attempts = db.query(TaskAttempt).filter(
        TaskAttempt.user_id == user_id,
        TaskAttempt.task_id == task_id
    ).order_by(TaskAttempt.submitted_at).all()

    if not attempts:
        return None

    # Get related objects
    user = db.query(User).filter(User.id == user_id).first()
    task = db.query(Task).filter(Task.id == task_id).first()
    course = get_course_from_task(task, db)

    if not user or not task or not course:
        return None

    # Check if analysis already exists
    existing_analysis = db.query(StudentTaskAnalysis).filter(
        StudentTaskAnalysis.user_id == user_id,
        StudentTaskAnalysis.task_id == task_id
    ).first()

    # If exists and task is complete, don't re-analyze (saves cost)
    if existing_analysis and existing_analysis.final_success:
        return existing_analysis

    # Calculate time gaps
    time_data = calculate_time_gaps(attempts)

    # Generate prompt
    prompt_data = generate_task_analysis_prompt(user, task, attempts, course)

    # Call OpenAI with structured output
    try:
        client = get_openai_client()

        response = client.beta.chat.completions.parse(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": prompt_data["system"]},
                {"role": "user", "content": prompt_data["user"]}
            ],
            response_format=TaskAnalysisSchema
            # Note: GPT-5 only supports default temperature (1)
        )

        # Extract structured analysis
        analysis_result = response.choices[0].message.parsed

        if not analysis_result:
            return None

        # Convert to dict for JSON storage
        analysis_dict = analysis_result.model_dump()

        # Generate professor notes (detailed technical summary)
        professor_notes = _generate_professor_notes_from_analysis(
            analysis_dict,
            task.task_name,
            len(attempts),
            time_data['total_time_spent']
        )

        # Prepare analysis data
        successful_attempts = len([a for a in attempts if a.is_successful])
        failed_attempts = len([a for a in attempts if not a.is_successful])
        outlier_flag = len(attempts) > 50

        if existing_analysis:
            # Update existing
            existing_analysis.total_attempts = len(attempts)
            existing_analysis.successful_attempts = successful_attempts
            existing_analysis.failed_attempts = failed_attempts
            existing_analysis.last_attempt_at = attempts[-1].submitted_at
            existing_analysis.final_success = attempts[-1].is_successful
            existing_analysis.attempt_time_gaps = json.dumps(time_data['attempt_time_gaps'], ensure_ascii=False)
            existing_analysis.total_time_spent = time_data['total_time_spent']
            existing_analysis.analysis = analysis_dict
            existing_analysis.professor_notes = professor_notes
            existing_analysis.analyzed_at = datetime.utcnow()
            existing_analysis.llm_model = LLM_MODEL_NAME
            existing_analysis.outlier_flag = outlier_flag

            db.commit()
            db.refresh(existing_analysis)
            return existing_analysis
        else:
            # Create new
            new_analysis = StudentTaskAnalysis(
                user_id=user_id,
                task_id=task_id,
                course_id=course.id,
                total_attempts=len(attempts),
                successful_attempts=successful_attempts,
                failed_attempts=failed_attempts,
                first_attempt_at=attempts[0].submitted_at,
                last_attempt_at=attempts[-1].submitted_at,
                final_success=attempts[-1].is_successful,
                attempt_time_gaps=json.dumps(time_data['attempt_time_gaps'], ensure_ascii=False),
                total_time_spent=time_data['total_time_spent'],
                analysis=analysis_dict,
                professor_notes=professor_notes,
                analyzed_at=datetime.utcnow(),
                llm_model=LLM_MODEL_NAME,
                analysis_version=1,
                outlier_flag=outlier_flag
            )

            db.add(new_analysis)
            db.commit()
            db.refresh(new_analysis)
            return new_analysis

    except Exception as e:
        # Log error but don't block submission
        print(f"Task analysis failed for user {user_id}, task {task_id}: {str(e)}")
        return None


def _generate_professor_notes_from_analysis(
    analysis: dict,
    task_name: str,
    attempt_count: int,
    total_time: str
) -> str:
    """
    Generate detailed professor notes from structured analysis.

    Args:
        analysis: Dictionary from TaskAnalysisSchema
        task_name: Name of the task
        attempt_count: Number of attempts
        total_time: Human-readable total time

    Returns:
        Formatted professor notes string
    """
    notes = f"Task: {task_name}\n"
    notes += f"Attempts: {attempt_count} over {total_time}\n\n"

    # Add task summary if available
    if 'task_summary' in analysis and analysis['task_summary']:
        notes += f"Task Summary: {analysis['task_summary']}\n\n"

    notes += f"Learning Progression: {analysis['learning_progression']}\n"
    notes += f"Difficulty Assessment: {analysis['difficulty_level']}\n"
    notes += f"Instructor Intervention Needed: {'Yes' if analysis['help_needed'] else 'No'}\n\n"

    if analysis.get('error_patterns'):
        notes += "Error Patterns:\n"
        for pattern in analysis['error_patterns']:
            notes += f"  - {pattern}\n"
        notes += "\n"

    if analysis.get('concept_gaps'):
        notes += "Concept Gaps:\n"
        for gap in analysis['concept_gaps']:
            notes += f"  - {gap}\n"
        notes += "\n"

    if analysis.get('strengths'):
        notes += "Demonstrated Strengths:\n"
        for strength in analysis['strengths']:
            notes += f"  - {strength}\n"

    return notes


async def analyze_lesson_progress(
    user_id: int,
    lesson_id: int,
    db: Session
) -> Optional[StudentLessonAnalysis]:
    """
    Analyze student's progress across all tasks in a lesson using OpenAI.

    Creates or updates StudentLessonAnalysis record with:
    - Aggregated task statistics
    - LLM-generated analysis (mastered/struggling concepts, pacing, retention)
    - Motivational student summary for frontend display

    Args:
        user_id: User ID
        lesson_id: Lesson ID
        db: Database session

    Returns:
        StudentLessonAnalysis object or None if analysis failed
    """
    from schemas.learning_analytics import LessonAnalysisSchema

    # Get lesson and course objects
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        return None

    course = db.query(Course).filter(Course.id == lesson.course_id).first()
    user = db.query(User).filter(User.id == user_id).first()

    if not course or not user:
        return None

    # Get all topics in this lesson
    topics = db.query(Topic).filter(Topic.lesson_id == lesson_id).all()
    topic_ids = [t.id for t in topics]

    # Get all ACTIVE code tasks in these topics
    tasks = db.query(Task).filter(
        Task.topic_id.in_(topic_ids),
        Task.type == 'code_task',
        Task.is_active == True
    ).all()

    if not tasks:
        return None

    task_ids = [t.id for t in tasks]

    # Get all task analyses for these tasks for this user
    task_analyses = db.query(StudentTaskAnalysis).filter(
        StudentTaskAnalysis.user_id == user_id,
        StudentTaskAnalysis.task_id.in_(task_ids)
    ).all()

    # If no task analyses exist yet, can't do lesson analysis
    if not task_analyses:
        return None

    # Calculate completion percentage
    completed_tasks = len([ta for ta in task_analyses if ta.final_success])
    completion_percentage = (completed_tasks / len(tasks)) * 100 if tasks else 0

    # Check if we need to update existing analysis
    existing_analysis = db.query(StudentLessonAnalysis).filter(
        StudentLessonAnalysis.user_id == user_id,
        StudentLessonAnalysis.lesson_id == lesson_id
    ).first()

    # Skip if existing analysis is up-to-date
    if existing_analysis and not needs_lesson_analysis_update(
        existing_analysis, completion_percentage
    ):
        return existing_analysis

    # Generate lesson analysis prompt
    prompt_data = generate_lesson_analysis_prompt(user, lesson, course, task_analyses)

    # Call OpenAI with structured output
    try:
        client = get_openai_client()

        # First call: Technical analysis
        response = client.beta.chat.completions.parse(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": prompt_data["system"]},
                {"role": "user", "content": prompt_data["user"]}
            ],
            response_format=LessonAnalysisSchema
        )

        analysis_result = response.choices[0].message.parsed

        if not analysis_result:
            return None

        # Convert to dict for JSON storage
        analysis_dict = analysis_result.model_dump()

        # Second call: Generate motivational student summary
        summary_prompt = generate_lesson_student_summary_prompt(
            analysis_dict, lesson.title
        )

        summary_response = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a supportive programming instructor writing encouraging messages to students. Write in Russian to match the course language."},
                {"role": "user", "content": summary_prompt}
            ]
        )

        student_summary = summary_response.choices[0].message.content.strip()

        # Calculate aggregate statistics
        total_tasks = len(tasks)
        solved_tasks = len([ta for ta in task_analyses if ta.final_success])

        # Calculate total points
        total_points_available = sum(t.points or 0 for t in tasks)
        points_earned = sum(ta.task.points or 0 for ta in task_analyses if ta.final_success)

        # Calculate time metrics
        all_first_attempts = [ta.first_attempt_at for ta in task_analyses]
        lesson_start_date = min(all_first_attempts) if all_first_attempts else datetime.utcnow()

        # Check if lesson is complete (all tasks solved)
        lesson_completion_date = None
        if solved_tasks == total_tasks and total_tasks > 0:
            all_last_attempts = [ta.last_attempt_at for ta in task_analyses]
            lesson_completion_date = max(all_last_attempts)

        # Calculate total lesson time
        if lesson_completion_date:
            time_delta = lesson_completion_date - lesson_start_date
            total_lesson_time = _humanize_duration(time_delta, len(task_analyses))
        else:
            total_lesson_time = "In progress"

        if existing_analysis:
            # Update existing
            existing_analysis.total_topics = len(topics)
            existing_analysis.completed_topics = len([t for t in topics if all(
                ta.final_success for ta in task_analyses if ta.task.topic_id == t.id
            )])
            existing_analysis.completion_percentage = completion_percentage
            existing_analysis.total_tasks = total_tasks
            existing_analysis.solved_tasks = solved_tasks
            existing_analysis.total_points_available = total_points_available
            existing_analysis.points_earned = points_earned
            existing_analysis.lesson_start_date = lesson_start_date
            existing_analysis.lesson_completion_date = lesson_completion_date
            existing_analysis.total_lesson_time = total_lesson_time
            existing_analysis.analysis = analysis_dict
            existing_analysis.student_summary = student_summary
            existing_analysis.analyzed_at = datetime.utcnow()
            existing_analysis.llm_model = LLM_MODEL_NAME

            db.commit()
            db.refresh(existing_analysis)
            return existing_analysis
        else:
            # Create new
            new_analysis = StudentLessonAnalysis(
                user_id=user_id,
                lesson_id=lesson_id,
                course_id=course.id,
                total_topics=len(topics),
                completed_topics=len([t for t in topics if all(
                    ta.final_success for ta in task_analyses if ta.task.topic_id == t.id
                )]),
                completion_percentage=completion_percentage,
                total_tasks=total_tasks,
                solved_tasks=solved_tasks,
                total_points_available=total_points_available,
                points_earned=points_earned,
                lesson_start_date=lesson_start_date,
                lesson_completion_date=lesson_completion_date,
                total_lesson_time=total_lesson_time,
                analysis=analysis_dict,
                student_summary=student_summary,
                analyzed_at=datetime.utcnow(),
                llm_model=LLM_MODEL_NAME,
                analysis_version=1
            )

            db.add(new_analysis)
            db.commit()
            db.refresh(new_analysis)
            return new_analysis

    except Exception as e:
        # Log error but don't break the flow
        print(f"Lesson analysis failed for user {user_id}, lesson {lesson_id}: {str(e)}")
        return None


async def analyze_course_profile(
    user_id: int,
    course_id: int,
    db: Session
) -> Optional[StudentCourseProfile]:
    """
    Analyze student's overall performance across entire course using OpenAI.

    Creates or updates StudentCourseProfile record with:
    - Course-wide statistics
    - LLM-generated profile (strengths, weaknesses, learning velocity, etc.)
    - Congratulatory student summary for course completion dashboard

    Args:
        user_id: User ID
        course_id: Course ID
        db: Database session

    Returns:
        StudentCourseProfile object or None if analysis failed
    """
    from schemas.learning_analytics import CourseProfileSchema

    # Get course and user objects
    course = db.query(Course).filter(Course.id == course_id).first()
    user = db.query(User).filter(User.id == user_id).first()

    if not course or not user:
        return None

    # Get all lessons in this course
    lessons = db.query(Lesson).filter(Lesson.course_id == course_id).all()
    lesson_ids = [l.id for l in lessons]

    # Get all lesson analyses for this user in this course
    lesson_analyses = db.query(StudentLessonAnalysis).filter(
        StudentLessonAnalysis.user_id == user_id,
        StudentLessonAnalysis.lesson_id.in_(lesson_ids)
    ).all()

    # If no lesson analyses exist, can't do course analysis
    if not lesson_analyses:
        return None

    # Get all task analyses for this course
    task_analyses = db.query(StudentTaskAnalysis).filter(
        StudentTaskAnalysis.user_id == user_id,
        StudentTaskAnalysis.course_id == course_id
    ).all()

    if not task_analyses:
        return None

    # Check if profile already exists
    existing_profile = db.query(StudentCourseProfile).filter(
        StudentCourseProfile.user_id == user_id,
        StudentCourseProfile.course_id == course_id
    ).first()

    # Skip if profile is recent (updated in last 7 days)
    if existing_profile and not is_course_profile_outdated(existing_profile, days_threshold=7):
        return existing_profile

    # Generate course profile prompt
    prompt_data = _generate_course_profile_prompt(user, course, lesson_analyses, task_analyses)

    # Call OpenAI with structured output
    try:
        client = get_openai_client()

        # First call: Technical profile analysis
        response = client.beta.chat.completions.parse(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": prompt_data["system"]},
                {"role": "user", "content": prompt_data["user"]}
            ],
            response_format=CourseProfileSchema
        )

        profile_result = response.choices[0].message.parsed

        if not profile_result:
            return None

        # Convert to dict for JSON storage
        profile_dict = profile_result.model_dump()

        # Second call: Generate congratulatory student summary
        summary_prompt = generate_course_student_summary_prompt(
            profile_dict, course.title
        )

        summary_response = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a supportive programming instructor writing congratulatory messages for course completion. Write in Russian to match the course language."},
                {"role": "user", "content": summary_prompt}
            ]
        )

        student_summary = summary_response.choices[0].message.content.strip()

        # Calculate aggregate statistics
        total_lessons = len(lessons)
        completed_lessons = len([la for la in lesson_analyses if la.completion_percentage == 100])

        # Calculate course completion percentage (only active tasks)
        all_tasks_in_course = db.query(Task).join(Topic).join(Lesson).filter(
            Lesson.course_id == course_id,
            Task.type == 'code_task',
            Task.is_active == True
        ).all()

        completed_task_count = len([ta for ta in task_analyses if ta.final_success])
        course_completion_percentage = (completed_task_count / len(all_tasks_in_course) * 100) if all_tasks_in_course else 0

        # Calculate total points
        total_course_points = sum(t.points or 0 for t in all_tasks_in_course)
        points_earned = sum(ta.task.points or 0 for ta in task_analyses if ta.final_success)

        # Calculate time metrics
        all_first_attempts = [ta.first_attempt_at for ta in task_analyses]
        course_start_date = min(all_first_attempts) if all_first_attempts else datetime.utcnow()

        all_last_attempts = [ta.last_attempt_at for ta in task_analyses]
        last_activity_date = max(all_last_attempts) if all_last_attempts else datetime.utcnow()

        # Check if course is complete
        course_completion_date = None
        if course_completion_percentage == 100:
            course_completion_date = last_activity_date

        # Calculate total course time
        if course_completion_date:
            time_delta = course_completion_date - course_start_date
            days = int(time_delta.total_seconds() / 86400)
            total_course_time = f"{days} days"
        else:
            time_delta = last_activity_date - course_start_date
            days = int(time_delta.total_seconds() / 86400)
            total_course_time = f"{days} days (in progress)"

        if existing_profile:
            # Update existing
            existing_profile.total_lessons = total_lessons
            existing_profile.completed_lessons = completed_lessons
            existing_profile.course_completion_percentage = course_completion_percentage
            existing_profile.total_course_points = total_course_points
            existing_profile.points_earned = points_earned
            existing_profile.course_start_date = course_start_date
            existing_profile.last_activity_date = last_activity_date
            existing_profile.course_completion_date = course_completion_date
            existing_profile.total_course_time = total_course_time
            existing_profile.analysis = profile_dict
            existing_profile.student_summary = student_summary
            existing_profile.analyzed_at = datetime.utcnow()
            existing_profile.llm_model = LLM_MODEL_NAME

            db.commit()
            db.refresh(existing_profile)
            return existing_profile
        else:
            # Create new
            new_profile = StudentCourseProfile(
                user_id=user_id,
                course_id=course_id,
                total_lessons=total_lessons,
                completed_lessons=completed_lessons,
                course_completion_percentage=course_completion_percentage,
                total_course_points=total_course_points,
                points_earned=points_earned,
                course_start_date=course_start_date,
                last_activity_date=last_activity_date,
                course_completion_date=course_completion_date,
                total_course_time=total_course_time,
                analysis=profile_dict,
                student_summary=student_summary,
                analyzed_at=datetime.utcnow(),
                llm_model=LLM_MODEL_NAME,
                analysis_version=1
            )

            db.add(new_profile)
            db.commit()
            db.refresh(new_profile)
            return new_profile

    except Exception as e:
        # Log error but don't break the flow
        print(f"Course profile analysis failed for user {user_id}, course {course_id}: {str(e)}")
        return None


def _generate_course_profile_prompt(
    user: User,
    course: Course,
    lesson_analyses: List[StudentLessonAnalysis],
    task_analyses: List[StudentTaskAnalysis]
) -> Dict[str, str]:
    """
    Generate LLM prompt for course-level profile synthesis.

    Args:
        user: User object
        course: Course object
        lesson_analyses: All StudentLessonAnalysis objects for this user/course
        task_analyses: All StudentTaskAnalysis objects for this user/course

    Returns:
        Dictionary with 'system' and 'user' prompts
    """
    # Format lesson analyses for LLM
    formatted_lessons = []
    for la in lesson_analyses:
        lesson = la.lesson
        formatted_lessons.append(f"""
Lesson: {lesson.title}
Completion: {la.completion_percentage}%
Tasks: {la.solved_tasks}/{la.total_tasks}
Analysis:
  - Mastered concepts: {', '.join(la.analysis.get('mastered_concepts', []))}
  - Struggling concepts: {', '.join(la.analysis.get('struggling_concepts', []))}
  - Pacing: {la.analysis.get('pacing', 'N/A')}
  - Retention score: {la.analysis.get('retention_score', 0)}
""")

    # Aggregate key metrics
    total_immediate_success = len([ta for ta in task_analyses if ta.analysis.get('learning_progression') == 'immediate_success'])
    total_struggle_breakthrough = len([ta for ta in task_analyses if ta.analysis.get('learning_progression') == 'struggle_then_breakthrough'])
    total_persistent_difficulty = len([ta for ta in task_analyses if ta.analysis.get('learning_progression') == 'persistent_difficulty'])

    system_prompt = f"""You are an expert programming educator creating a comprehensive student profile for a {course.language or 'Python'} course.

Synthesize patterns across all lessons and tasks to identify:
1. Core programming strengths consistently demonstrated
2. Persistent weaknesses that need targeted practice
3. Learning velocity and trajectory
4. Resilience and recovery from failures
5. Preferred learning style
6. Readiness for advanced topics

Provide actionable recommendations for the student's continued growth."""

    user_prompt = f"""STUDENT: {user.username} (ID: {user.id})
COURSE: {course.title}

COURSE OVERVIEW:
Total Lessons: {len(lesson_analyses)}
Total Tasks Attempted: {len(task_analyses)}
Tasks Completed: {len([ta for ta in task_analyses if ta.final_success])}

LEARNING PROGRESSION BREAKDOWN:
- Immediate Success: {total_immediate_success} tasks
- Struggle then Breakthrough: {total_struggle_breakthrough} tasks
- Persistent Difficulty: {total_persistent_difficulty} tasks

LESSON-LEVEL SUMMARIES:
{''.join(formatted_lessons)}

ANALYSIS REQUIREMENTS:
1. core_strengths: List 2-3 programming skills consistently demonstrated across lessons
2. persistent_weaknesses: List 2-3 concepts that remained challenging despite practice
3. learning_velocity: Assess as ONE of: "rapid_improvement", "steady_progress", "plateaued", "declining"
4. resilience_score: Float 0.0-1.0 indicating ability to recover from failures and persist
5. preferred_learning_style: Identify as ONE of: "visual_with_examples", "trial_and_error", "concept_first", "pattern_recognition"
6. readiness_for_advanced: Boolean - whether student is ready for advanced topics
7. concept_graph: Nested object with:
   - strong_foundations: List concepts with high retention/transfer
   - weak_connections: List topic transitions where student struggled
8. recommended_practice: List 2-3 practice recommendations with:
   - concept: Specific concept to practice
   - difficulty: "beginner", "intermediate", or "advanced"
   - count: Number of practice tasks (1-10)

Respond in JSON format with exactly these keys."""

    return {
        "system": system_prompt,
        "user": user_prompt
    }
