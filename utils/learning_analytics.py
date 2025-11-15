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
# Using gpt-5-mini for cost savings while maintaining good technical quality
LLM_MODEL_NAME = "gpt-5-mini"


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
        for i, attempt in enumerate(attempts, 1):
            status = "✓" if attempt.is_successful else "✗"
            code = attempt.attempt_content[:600] if attempt.attempt_content else "[No code submitted]"

            formatted_attempts.append(
                f"Attempt {i} [{status}]:\n{code}"
            )
        return "\n\n".join(formatted_attempts)
    else:
        # Outlier case: show first 5 + last 15 (for students with many attempts)
        first_five = attempts[:5]
        last_fifteen = attempts[-15:]

        formatted_attempts = []

        # First 5
        for i, attempt in enumerate(first_five, 1):
            status = "✓" if attempt.is_successful else "✗"
            code = attempt.attempt_content[:400] if attempt.attempt_content else "[No code]"
            formatted_attempts.append(f"Attempt {i} [{status}]:\n{code}")

        # Gap indicator
        formatted_attempts.append(f"... [{len(attempts) - 20} attempts omitted] ...")

        # Last 15
        for i, attempt in enumerate(last_fifteen):
            attempt_num = len(attempts) - 15 + i + 1
            status = "✓" if attempt.is_successful else "✗"
            code = attempt.attempt_content[:400] if attempt.attempt_content else "[No code]"
            formatted_attempts.append(f"Attempt {attempt_num} [{status}]:\n{code}")

        return "\n\n".join(formatted_attempts)


# ===============================================================================
# Task Summary Generation (Pre-compute once per task)
# ===============================================================================


def generate_task_summary(task: Task, course: Course) -> Optional[str]:
    """
    Generate a one-line summary of what knowledge/skill this task tests and trains.

    This should be called once per task (when task is created/updated) and stored
    in task.task_summary field. This avoids regenerating the same summary for every
    student who attempts the task.

    Args:
        task: Task object with data JSON (contains 'text' instruction and 'code' starter)
        course: Course object for context (language, etc.)

    Returns:
        One-line summary string (e.g., "Tests for loop iteration and string indexing")
        or None if generation fails
    """
    # Extract task instruction and starter code from data JSON
    if not isinstance(task.data, dict):
        return f"Coding task: {task.task_name}"

    task_instruction = task.data.get('text', '')
    starter_code = task.data.get('code', '')

    if not task_instruction:
        # No instruction to analyze
        return f"Coding task: {task.task_name}"

    # Generate summary using OpenAI
    try:
        client = get_openai_client()

        response = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": f"You are an expert programming educator analyzing tasks in a {course.language or 'Python'} course. Generate concise, specific summaries of what skills/knowledge each task tests."
                },
                {
                    "role": "user",
                    "content": f"""Analyze this programming task and generate a HIGH-LEVEL, CONCEPTUAL summary (max 100 characters) of what programming concept/skill it teaches.

TASK: {task.task_name}
TYPE: {task.type}

INSTRUCTION:
{task_instruction}

STARTER CODE:
{starter_code if starter_code else '[No starter code]'}

Requirements:
- Focus on the CORE CONCEPT being taught, not specific task details
- Be abstract and generalizable (e.g., "string slicing" not "slice [4:8]")
- Use programming terminology, not task-specific values
- Keep it short and conceptual
- Start with "Tests..." or "Practices..." or "Applies..."
- DO NOT repeat specific variable names, indices, or task details

Good examples (abstract, conceptual):
- "Tests basic string indexing and slicing with step parameter"
- "Practices list comprehension with conditional filtering"
- "Applies dictionary methods for data aggregation"
- "Tests loop iteration with range and enumerate functions"

Bad examples (too specific, repeating task):
- "Tests getting first char, slice [4:8], and every second char"
- "Practices creating list with numbers 1 to 10 using append"
- "Tests printing 'Python' character by character"

Generate ONLY the one-line conceptual summary, no additional text."""
                }
            ]
        )

        summary = response.choices[0].message.content.strip()

        # Ensure it's not too long
        if len(summary) > 200:
            summary = summary[:197] + "..."

        return summary

    except Exception as e:
        print(f"Failed to generate task summary for task {task.id}: {str(e)}")
        return f"{task.type.replace('_', ' ').title()}: {task.task_name}"


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

    # Extract task information from data JSON (text and code fields)
    task_instruction = ""
    starter_code = ""

    if isinstance(task.data, dict):
        task_instruction = task.data.get('text', 'No instruction provided')
        starter_code = task.data.get('code', '')

    # Get pre-generated task summary (what this task tests/trains)
    task_summary = task.task_summary or f"Coding task: {task.task_name}"

    system_prompt = f"""You are an expert programming educator analyzing student learning patterns in a {course.language or 'Python'} course.

Analyze attempts to identify: error patterns, learning progression, concept gaps, strengths, and difficulty appropriateness.
Be specific and reference actual code patterns."""

    # Generate human-readable attempt summary
    successful_count = len([a for a in attempts if a.is_successful])
    failed_count = len([a for a in attempts if not a.is_successful])

    if len(attempts) == 1:
        if attempts[0].is_successful:
            attempt_summary = "Solved on first attempt"
        else:
            attempt_summary = "Made 1 attempt (not yet solved)"
    else:
        if successful_count > 0:
            # Find which attempt succeeded
            for i, a in enumerate(attempts, 1):
                if a.is_successful:
                    attempt_summary = f"Solved on attempt {i} of {len(attempts)}"
                    break
        else:
            attempt_summary = f"Made {len(attempts)} attempts (not yet solved)"

    user_prompt = f"""STUDENT ID: {user.id}
COURSE ID: {course.id}

TASK TESTS:
{task_summary}

INSTRUCTION:
{task_instruction}

STARTER CODE:
{starter_code if starter_code else '[No starter code]'}

ATTEMPTS: {attempt_summary}
Time spent: {time_data['total_time_spent']}

ALL ATTEMPTS:
{_format_attempts_for_llm(attempts, max_show=20)}

ANALYZE (respond in JSON):
- error_patterns: List 0-3 specific error patterns (empty if none)
- learning_progression: "immediate_success" | "struggle_then_breakthrough" | "persistent_difficulty"
- concept_gaps: List 0-3 specific concept gaps (empty if none)
- strengths: List 1-2 demonstrated strengths
- help_needed: true if needs instructor intervention (same error 3+ times)
- difficulty_level: "too_easy" | "appropriate" | "too_hard"
"""

    return {
        "system": system_prompt,
        "user": user_prompt
    }


# ===============================================================================
# Lesson-Level Analysis Prompt Generation
# ===============================================================================


def _calculate_class_statistics(lesson_id: int, db: Session) -> Dict[str, Any]:
    """
    Calculate class-wide statistics for a lesson to provide comparison context.

    Args:
        lesson_id: Lesson ID to get stats for
        db: Database session

    Returns:
        Dictionary with class averages and formatted comparison text
    """
    # Get all lesson analyses for this lesson (from other students)
    all_lesson_analyses = db.query(StudentLessonAnalysis).filter(
        StudentLessonAnalysis.lesson_id == lesson_id
    ).all()

    if not all_lesson_analyses or len(all_lesson_analyses) < 3:
        # Not enough data for meaningful comparison
        return {
            'comparison_text': 'CLASS COMPARISON: Not enough class data available yet for comparison.',
            'avg_completion': None,
            'avg_retention': None,
            'avg_attempts': None
        }

    # Calculate class averages
    completions = [la.completion_percentage for la in all_lesson_analyses]
    avg_completion = sum(completions) / len(completions)

    retentions = [la.analysis.get('retention_score', 0) for la in all_lesson_analyses]
    avg_retention = sum(retentions) / len(retentions)

    # Get all task analyses for this lesson to calculate average attempts
    all_task_analyses = db.query(StudentTaskAnalysis).join(
        Task, StudentTaskAnalysis.task_id == Task.id
    ).join(
        Topic, Task.topic_id == Topic.id
    ).filter(
        Topic.lesson_id == lesson_id
    ).all()

    if all_task_analyses:
        # Calculate average attempts per student
        student_avg_attempts = {}
        for ta in all_task_analyses:
            if ta.user_id not in student_avg_attempts:
                student_avg_attempts[ta.user_id] = []
            student_avg_attempts[ta.user_id].append(ta.total_attempts)

        # Calculate class average (average of each student's average)
        student_averages = [sum(attempts) / len(attempts) for attempts in student_avg_attempts.values() if attempts]
        class_avg_attempts = sum(student_averages) / len(student_averages) if student_averages else None
    else:
        class_avg_attempts = None

    # Format comparison text
    comparison_lines = ["CLASS COMPARISON (for calibration):"]
    comparison_lines.append(f"- Class average completion: {avg_completion:.1f}%")
    comparison_lines.append(f"- Class average retention: {avg_retention:.2f}")
    if class_avg_attempts:
        comparison_lines.append(f"- Class average attempts per task: {class_avg_attempts:.1f}")
    comparison_lines.append(f"- Total students analyzed: {len(all_lesson_analyses)}")

    return {
        'comparison_text': '\n'.join(comparison_lines),
        'avg_completion': avg_completion,
        'avg_retention': avg_retention,
        'avg_attempts': class_avg_attempts
    }


def generate_lesson_analysis_prompt(
    user: User,
    lesson: Lesson,
    course: Course,
    task_analyses: List[StudentTaskAnalysis],
    db: Session
) -> Dict[str, str]:
    """
    Generate LLM prompt for lesson-level synthesis.

    Args:
        user: User object
        lesson: Lesson object being analyzed
        course: Course object for context
        task_analyses: All StudentTaskAnalysis objects for tasks in this lesson
        db: Database session for class statistics

    Returns:
        Dictionary with 'system' and 'user' prompts
    """
    # Calculate aggregate attempt statistics for this student
    all_attempts = [ta.total_attempts for ta in task_analyses]
    avg_attempts = sum(all_attempts) / len(all_attempts) if all_attempts else 0

    # Calculate median
    sorted_attempts = sorted(all_attempts)
    if len(sorted_attempts) % 2 == 0:
        median_attempts = (sorted_attempts[len(sorted_attempts)//2 - 1] + sorted_attempts[len(sorted_attempts)//2]) / 2
    else:
        median_attempts = sorted_attempts[len(sorted_attempts)//2]

    # Count learning progression patterns
    immediate_count = len([ta for ta in task_analyses if ta.analysis.get('learning_progression') == 'immediate_success'])
    struggle_count = len([ta for ta in task_analyses if ta.analysis.get('learning_progression') == 'struggle_then_breakthrough'])
    difficult_count = len([ta for ta in task_analyses if ta.analysis.get('learning_progression') == 'persistent_difficulty'])

    # Get class comparison data (if available)
    class_stats = _calculate_class_statistics(lesson.id, db)

    # Format task analyses for LLM (compressed format)
    formatted_tasks = []
    for i, ta in enumerate(task_analyses, 1):
        task = ta.task
        # Use pre-generated task_summary from task table (what skill this task tests)
        task_summary = task.task_summary or f"Coding task: {task.task_name}"

        progression = ta.analysis.get('learning_progression', 'N/A')
        gaps = ta.analysis.get('concept_gaps', [])
        strengths = ta.analysis.get('strengths', [])

        # Build compressed format
        parts = [
            f"{i}. {task_summary} ({ta.total_attempts} attempts)",
            f"   Progression: {progression}"
        ]

        if gaps:
            parts.append(f"   Gaps: {', '.join(gaps)}")
        if strengths:
            parts.append(f"   Strengths: {', '.join(strengths)}")

        formatted_tasks.append('\n'.join(parts))

    system_prompt = f"""You are an expert programming educator synthesizing a student's lesson-level progress in a {course.language or 'Python'} course.

Analyze patterns across multiple tasks to identify:
1. Concepts mastered vs struggling
2. Content difficulty match (overwhelmed/appropriate/under-challenged) - NOT student speed, but whether content difficulty is well-matched to student's current level
3. Retention across topics
4. Help-seeking patterns
5. Topic dependency issues

Provide actionable insights for lesson design and student support."""

    user_prompt = f"""STUDENT ID: {user.id}
COURSE ID: {course.id}
LESSON: {lesson.title}

DESCRIPTION: {lesson.description}
TOPICS: {len(lesson.topics)}
TASKS ANALYZED: {len(task_analyses)}

ATTEMPT STATS:
- Avg: {avg_attempts:.1f}, Median: {median_attempts:.1f}, Range: {min(all_attempts)}-{max(all_attempts)}
- Patterns: {immediate_count} immediate, {struggle_count} struggle→breakthrough, {difficult_count} persistent

{class_stats['comparison_text']}

TASK SUMMARIES:
{chr(10).join(formatted_tasks)}

ANALYZE (respond in JSON):
- mastered_concepts: List 2-4 concepts appearing as strengths across tasks
- struggling_concepts: List 2-4 concepts appearing as gaps across tasks
- pacing: "overwhelmed" (struggling, attempts >> class avg) | "appropriate" (attempts ≈ class avg, mix of patterns) | "under_challenged" (1-2 attempts, mostly immediate success)
- retention_score: Float 0.0-1.0 (tasks showing retention / tasks with opportunity)
- help_seeking_pattern: "too_frequent" (5+ same errors, no learning) | "appropriate" (productive retries) | "too_rare" (gives up after 1-2 attempts)
- topic_dependencies_issues: List "Weak [concept] → struggled with [later concept in tasks]"
"""

    return {
        "system": system_prompt,
        "user": user_prompt
    }


# ===============================================================================
# Student Summary Generation (Lesson & Course Levels)
# ===============================================================================


def generate_lesson_student_summary_prompt(
    analysis_data: dict,
    lesson_title: str,
    user: User,
    task_analyses: List[StudentTaskAnalysis],
    previous_messages: List[str] = None
) -> str:
    """
    Generate prompt to create motivational lesson summary for students.

    Args:
        analysis_data: The JSON analysis from lesson-level LLM call
        lesson_title: Title of the lesson
        user: User object for personalization
        task_analyses: List of StudentTaskAnalysis objects for specific context
        previous_messages: Optional list of previous motivational messages to avoid repetition

    Returns:
        Prompt string for generating student-friendly summary
    """
    # Build personalization context
    personalization = ""
    if user.first_name:
        personalization = f"\n\nStudent's first name: {user.first_name.capitalize()}\nUse it naturally in your message."

    # Build previous messages context
    previous_context = ""
    if previous_messages and len(previous_messages) > 0:
        previous_context = "\n\nPREVIOUS MESSAGES TO THIS STUDENT:\n"
        for i, msg in enumerate(previous_messages[-3:], 1):  # Show last 3 messages max
            previous_context += f"{i}. {msg}\n"
        previous_context += "\n⚠️ CRITICAL: Do NOT repeat phrases, vocabulary, or concepts from above. Show progression and use completely different language."

    # Build specific learning journey context
    journey_details = "\n\nLEARNING JOURNEY IN THIS LESSON:\n"

    # Find struggle-to-success stories
    struggle_stories = []
    for i, ta in enumerate(task_analyses, 1):
        if ta.analysis.get('learning_progression') == 'struggle_then_breakthrough':
            task_summary = ta.task.task_summary or ta.task.task_name
            attempts = ta.total_attempts
            concepts = ta.analysis.get('concept_gaps', [])
            struggle_stories.append(f"Task {i}: {task_summary[:60]} - {attempts} attempts, overcame: {', '.join(concepts[:2])}")

    if struggle_stories:
        journey_details += "Struggles → Breakthroughs:\n"
        for story in struggle_stories[:2]:  # Show max 2 stories
            journey_details += f"  • {story}\n"

    # Find immediate successes (for showing confidence)
    immediate_wins = []
    for i, ta in enumerate(task_analyses, 1):
        if ta.analysis.get('learning_progression') == 'immediate_success':
            task_summary = ta.task.task_summary or ta.task.task_name
            strengths = ta.analysis.get('strengths', [])
            if strengths:
                immediate_wins.append(f"Task {i}: {task_summary[:60]} - {strengths[0]}")

    if immediate_wins:
        journey_details += "\nImmediate Successes (shows mastery):\n"
        for win in immediate_wins[:2]:  # Show max 2
            journey_details += f"  • {win}\n"

    # Learning pattern metadata
    retention = analysis_data.get('retention_score', 0)
    pacing = analysis_data.get('pacing', 'appropriate')
    help_seeking = analysis_data.get('help_seeking_pattern', 'appropriate')

    learning_pattern = f"\n\nLEARNING PATTERN:\n"
    learning_pattern += f"- Retention: {retention:.0%} (how much they remember across tasks)\n"
    learning_pattern += f"- Pacing: {pacing} (content difficulty match)\n"
    learning_pattern += f"- Help-seeking: {help_seeking}\n"

    # Generic phrases to avoid
    avoid_phrases = """
STRICTLY AVOID these generic phrases:
❌ "отличная работа"
❌ "вы на правильном пути" / "на верном пути"
❌ "продолжайте в том же духе"
❌ "особенно впечатляет"
❌ "замечательно продвигаетесь"
❌ "уверенно работаете"
❌ "готовы к более сложным заданиям"
"""

    return f"""Based on this technical analysis of a student's progress in "{lesson_title}":

{json.dumps(analysis_data, indent=2, ensure_ascii=False)}
{personalization}
{journey_details}
{learning_pattern}
{previous_context}
{avoid_phrases}

🎯 YOUR TASK: Write a PERSONAL, NARRATIVE-DRIVEN message (2-3 sentences) that feels like a real teacher watched this specific student's journey.

CREATE A NARRATIVE ARC:
1. OPEN with a specific struggle-to-success moment OR reference a specific task number
2. USE a vivid metaphor relating programming to everyday life
3. ACKNOWLEDGE their learning style (retention {retention:.0%}, pacing: {pacing})
4. CLOSE with forward-looking anticipation (what's next)

REQUIREMENTS:
✓ Use polite Russian "вы" (not "ты")
✓ Start with their first name naturally
✓ Reference at least ONE specific task number or struggle mentioned above
✓ Include ONE vivid, memorable metaphor
✓ Show transformation (from confusion → clarity, from struggling → mastering)
✓ Use COMPLETELY NEW vocabulary (check previous messages!)
✓ Be specific about THIS lesson (not generic praise)

STYLE:
- Conversational, warm, observant (like you watched them work)
- Show you understand their SPECIFIC journey
- Use fresh, vivid language (metaphors, comparisons)
- Celebrate specific victories, not abstract concepts

BAD (generic, repetitive):
"Мария, отличная работа! Вы уверенно работаете со списками. Продолжайте в том же духе."

GOOD (specific, narrative, personal):
"Мария, задание 7 с сортировкой явно заставило задуматься — но теперь вы разбираетесь в методах списков как опытный библиотекарь в каталоге! С вашей способностью запоминать концепции (90%), словари покорятся вам с той же лёгкостью."

Write ONLY the student message in Russian, no commentary."""


def generate_course_student_summary_prompt(analysis_data: dict, course_title: str, user: User) -> str:
    """
    Generate prompt to create congratulatory course summary for students.

    Args:
        analysis_data: The JSON analysis from course-level LLM call
        course_title: Title of the course
        user: User object for personalization

    Returns:
        Prompt string for generating congratulatory dashboard message
    """
    # Build personalization context
    personalization = ""
    if user.first_name:
        personalization = f"\n\nStudent's first name: {user.first_name}\nFeel free to use it naturally in your message if appropriate."

    return f"""Based on this comprehensive analysis of a student's progress in "{course_title}":

{json.dumps(analysis_data, indent=2, ensure_ascii=False)}
{personalization}

Write a congratulatory message (3-4 sentences) for the student's dashboard that:
- Use polite Russian address "вы" (not informal "ты") while maintaining a friendly, encouraging tone
- If first name is provided above, you may use it naturally in a warm greeting
- Celebrates their course completion with specific achievements
- Highlights 2-3 core strengths they've developed
- Acknowledges growth areas and frames them as future opportunities
- Encourages continued learning with enthusiasm

Avoid: generic praise, mentioning "analysis", dwelling on weaknesses, using informal "ты"
Focus on: transformation, specific skills gained, readiness for advanced topics, pride in achievement, polite but warm and friendly tone

Examples of good tone:
- "Алексей, поздравляем с завершением курса! Вы проделали большой путь и освоили все базовые концепции программирования. Ваша настойчивость и внимание к деталям впечатляют – продолжайте в том же духе!"
- "Поздравляем с завершением курса! Вы отлично справились со всеми темами и готовы к более сложным задачам."

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
        analysis: Dictionary from TaskAnalysisSchema (no longer includes task_summary)
        task_name: Name of the task
        attempt_count: Number of attempts
        total_time: Human-readable total time

    Returns:
        Formatted professor notes string

    Note: task_summary is no longer part of analysis dict. It's pre-generated
    and stored in task.task_summary field for efficiency.
    """
    notes = f"Task: {task_name}\n"
    notes += f"Attempts: {attempt_count} over {total_time}\n\n"

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

    # Get all ACTIVE tasks that use TaskAttempt tracking (code_task + assignment_submission)
    # Note: We only analyze tasks tracked via TaskAttempt, not quizzes (which are quick and don't need detailed analysis)
    tasks = db.query(Task).filter(
        Task.topic_id.in_(topic_ids),
        Task.type.in_(['code_task', 'assignment_submission']),
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
    prompt_data = generate_lesson_analysis_prompt(user, lesson, course, task_analyses, db)

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

        # Get previous lesson analyses for this student in the same course to avoid repetition
        previous_analyses = db.query(StudentLessonAnalysis).join(
            Lesson, StudentLessonAnalysis.lesson_id == Lesson.id
        ).filter(
            StudentLessonAnalysis.user_id == user_id,
            Lesson.course_id == course.id,
            StudentLessonAnalysis.lesson_id != lesson_id,  # Exclude current lesson
            StudentLessonAnalysis.student_summary.isnot(None)  # Only those with summaries
        ).order_by(StudentLessonAnalysis.analyzed_at).all()

        # Extract previous messages (last 3 to show progression)
        previous_messages = [la.student_summary for la in previous_analyses if la.student_summary]

        # Second call: Generate motivational student summary
        summary_prompt = generate_lesson_student_summary_prompt(
            analysis_dict, lesson.title, user, task_analyses, previous_messages
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
            profile_dict, course.title, user
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
