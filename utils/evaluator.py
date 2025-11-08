import os
from pydantic import BaseModel
from openai import OpenAI

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


client = OpenAI(api_key=OPENAI_API_KEY)


def get_language_instruction(language: str) -> str:
    """Get language-specific instruction for AI prompts"""
    if language and language.lower() == "russian":
        return "IMPORTANT: Provide all feedback, explanations, and guidance in RUSSIAN language. Use proper Russian grammar and vocabulary appropriate for programming education. ALWAYS use formal address (вы, вам, вас) when speaking to students, not informal (ты, тебе, тебя)."
    else:
        return "IMPORTANT: Provide all feedback, explanations, and guidance in ENGLISH language."


class SubmissionGrader(BaseModel):
    feedback: str
    is_solved: bool


def build_attempt_context(previous_attempts):
    """Extract and format attempt history context, including AI feedback."""
    if not previous_attempts:
        return "", 0, 0

    attempt_context = "\n\n**STUDENT'S LEARNING HISTORY**:\n"

    # Show up to 3 most recent previous attempts
    recent_attempts = previous_attempts[-3:] if len(previous_attempts) > 3 else previous_attempts

    for i, attempt in enumerate(recent_attempts, 1):
        attempt_status = "✓ Successful" if attempt.is_successful else "✗ Failed"
        code_content = attempt.attempt_content if attempt.attempt_content else "[No code]"
        attempt_context += f"\nAttempt {attempt.attempt_number} [{attempt_status}]:\n{code_content}\n"

        # Include AI feedback if available (show in full for effective anti-repetition)
        # Note: ai_feedback is a list (backref), so we get the last feedback if multiple exist
        if hasattr(attempt, 'ai_feedback') and attempt.ai_feedback:
            feedback_obj = attempt.ai_feedback[-1]  # Get most recent feedback
            feedback_text = feedback_obj.feedback
            attempt_context += f"AI Feedback given: {feedback_text}\n"

    # Calculate failed attempts
    failed_count = len([a for a in previous_attempts if not a.is_successful])

    # Add context awareness
    attempt_context += f"\n**Context Awareness:**\n"
    attempt_context += f"- Total attempts: {len(previous_attempts)}\n"
    attempt_context += f"- Failed attempts: {failed_count}\n"

    return attempt_context, len(previous_attempts), failed_count


def get_socratic_instructions(use_socratic, attempt_count, failed_count):
    """Generate Socratic method instructions (always in English for AI)."""
    if not use_socratic:
        return ""

    # Adjust questioning based on attempt count
    if attempt_count == 0:
        level = "Attempt 0: Broad questions. LIMIT: 1 sentence, 1-2 questions\n"
    elif attempt_count <= 2:
        level = "Attempts 1-2: Focused questions about code behavior. LIMIT: 1-2 sentences, 2-3 questions\n"
    elif attempt_count <= 4:
        level = "Attempts 3-4: Narrower hints with 'What if...?'. LIMIT: 2-3 sentences, 3-4 questions\n"
    else:
        level = "Attempts 5+: Step-by-step guidance. LIMIT: 3-4 sentences, 4-5 questions\n"

    return f"""SOCRATIC METHOD:
You are a Socratic teacher. Guide students to discover solutions through questions.

CORE PRINCIPLES:
- NEVER provide working code or method names (like .count(), .lower())
- Ask questions that lead to discovery
- Use student's code as starting point for inquiry

{level}
Examples:
❌ "Use .lower().count()" → ✓ "If all letters had same case, would searching be easier?"
❌ "You need a for loop" → ✓ "How can you go through all elements?"
"""


def build_system_prompt(language_instruction, socratic_instructions, use_socratic):
    """Build the complete system prompt (always in English)."""
    if use_socratic:
        feedback_section = """
**CORRECT CODE (is_solved=true)**:
- If previous attempts = 0: Celebrate first-try success (1-2 sentences, explain what they applied)
- If previous attempts 1-2: Warm congratulations (2 sentences: achievement + key technique)
- If previous attempts 3+: EMOTIONAL & BRIEF (1-2 sentences: celebration of perseverance, minimal technical detail)

**INCORRECT CODE (is_solved=false)**:
- **CRITICAL: AVOID REPETITION** - Check "AI Feedback given" in learning history. Do NOT repeat previous hints
- Build progressively: address different aspects, go deeper, provide new perspective
- Use "What if..." and "Why do you think..." questioning patterns
- Follow length limits specified in user message
"""
    else:
        feedback_section = """
Provide feedback that:
- Acknowledges progress from previous attempts
- Offers specific hints when stuck (multiple failed attempts)
- Guides without revealing solution
- **AVOID REPETITION**: Check "AI Feedback given" to build upon previous guidance
"""

    return f"""Evaluate student's Python code submission with contextual, progressive feedback.

{socratic_instructions}

{feedback_section}

{language_instruction}

Students learn through struggle. Help them discover solutions themselves."""


def build_user_prompt(task, answer, output, attempt_context, use_socratic, attempt_count, student_first_name=None):
    """Build the user prompt with appropriate instructions."""
    student_context = f"\n**Student name**: {student_first_name}" if student_first_name else ""

    # Only include output if it's not empty
    output_section = f"\n\n**Execution output:**\n{output}" if output and output.strip() else ""

    prompt = f"""Task: {task.data}

**Student's submitted code:**
{answer}{output_section}
{attempt_context}{student_context}

**Attempts: {attempt_count}**"""

    if use_socratic:
        if attempt_count > 0:
            prompt += "\n\nIMPORTANT: Review previous 'AI Feedback given' above. Do NOT repeat hints."
        prompt += "\n\nEvaluate if code solves task correctly. Apply Socratic method and length limits from system instructions."
    else:
        prompt += "\n\nProvide brief, contextual feedback (1-2 sentences)."

    return prompt


def provide_code_feedback(
    answer: str,
    output: str,
    task: dict,
    language: str = "English",
    previous_attempts: list = None,
    use_socratic_method: bool = True,
    student_first_name: str = None,
):
    """
    Provide AI-generated feedback for code submission.

    Args:
        answer: Current code submission
        output: Execution output of the code
        task: Task object with description
        language: Language for feedback (English/Russian)
        previous_attempts: List of previous TaskAttempt objects for context
        use_socratic_method: Whether to use Socratic questioning approach
        student_first_name: Student's first name for gender-aware verb forms

    Returns:
        SubmissionGrader with feedback and is_solved status
    """

    language_instruction = get_language_instruction(language)

    # Build context from previous attempts if available
    attempt_context, attempt_count, failed_count = build_attempt_context(previous_attempts)

    # Get Socratic instructions (always in English)
    socratic_instructions = get_socratic_instructions(
        use_socratic_method,
        attempt_count,
        failed_count
    )

    # Build system prompt (always in English)
    system_prompt = build_system_prompt(
        language_instruction,
        socratic_instructions,
        use_socratic_method
    )

    # Build user prompt with guidance
    user_prompt = build_user_prompt(
        task,
        answer,
        output,
        attempt_context,
        use_socratic_method,
        attempt_count,
        student_first_name
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=SubmissionGrader,
    )

    result = completion.choices[0].message.parsed
    return result


def provide_text_feedback(
    answer: str,
    task: dict,
    language: str = "English",
):

    language_instruction = get_language_instruction(language)

    system_prompt = (
        f"{language_instruction}\n\n"
        "You are an AI assistant tasked with evaluating a student's submission. "
        "You will be provided with the task description and the student's answer. "
        "Your job is to analyze the text and provide feedback based on the task requirements. "
        "Please follow these steps to evaluate the student's answer:\n"
        "1. Carefully read the task description and the student's answer.\n"
        "2. Check if the student's response addresses the task requirements.\n"
        "3. Evaluate the text for clarity, coherence, and relevance to the task.\n"
        "4. Provide constructive feedback that will help the student improve their writing skills.\n"
        "Remember to be supportive and encouraging in your feedback, focusing on helping the student."
    )

    user_prompt = (
        f"Here is the task description: {task}.\n"
        f"The student's answer is: {answer}\n"
        "Give feedback. Be polite and brief."
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=SubmissionGrader,
    )
    result = completion.choices[0].message.parsed

    return result


def evaluate_code_submission(submission, output, task, language="English", previous_attempts=None, student_first_name=None):
    """
    Evaluate a code submission for a task.
    :param submission: a code submission
    :param output: execution output
    :param task: a task
    :param language: language for AI feedback
    :param previous_attempts: list of previous TaskAttempt objects for context
    :param student_first_name: student's first name for gender-aware verb forms
    :return: a dictionary with the evaluation results
    """
    answer = submission["code"]
    feedback = provide_code_feedback(answer, output, task, language, previous_attempts, student_first_name=student_first_name)

    return feedback


def evaluate_text_submission(answer, task, language="English"):
    """
    Evaluate a text submission for a task.
    :param answer: a text submission
    :param task: a task
    :param language: language for AI feedback
    :param return: a tuple with a boolean indicating correctness and a feedback message
    """
    feedback = provide_text_feedback(answer, task, language)
    return feedback


def build_screenshot_system_prompt(language_instruction, task_description, task_title):
    """Build the system prompt for screenshot evaluation (similar to code evaluation)."""

    # Extract just the text description if task_description is a dict
    description_text = task_description
    has_starter_code = False

    if isinstance(task_description, dict):
        if 'text' in task_description:
            description_text = task_description['text']
        if 'code' in task_description:
            has_starter_code = True

    starter_code_note = ""
    if has_starter_code:
        starter_code_note = """
**CRITICAL INSTRUCTION:**
The task description includes "starter code" (a draft/template provided to students).
This starter code is NOT the student's solution - it's just a starting point.
The student's ACTUAL CODE is visible in the screenshot.
Evaluate ONLY what you see in the screenshot image, not the starter code in the text description.
"""

    return f"""Evaluate student's assignment screenshot submission with clear, constructive feedback.

{language_instruction}

ASSIGNMENT TASK:
Title: {task_title}
Description: {description_text}

{starter_code_note}

EVALUATION PRINCIPLES:
- Verify the screenshot demonstrates completion according to the assignment requirements
- Check for all required elements mentioned in the task description
- Look for visible errors or issues in the screenshot
- Analyze the CODE VISIBLE IN THE SCREENSHOT (not any starter code in the description)
- Provide clear guidance without simply giving the answer

FEEDBACK GUIDELINES:
**CORRECT SUBMISSION (is_solved=true)**:
- Congratulate the student warmly (1-2 sentences)
- Acknowledge what they demonstrated correctly
- Be encouraging and positive

**INCORRECT SUBMISSION (is_solved=false)**:
- Point out what's missing or incorrect (be specific)
- Provide a helpful hint on how to fix the issue
- Keep feedback brief but actionable (2-3 sentences)
- If screenshot doesn't match the assignment, politely ask to retake it

Students learn through doing. Help them understand what's needed to complete the assignment successfully."""


def build_screenshot_user_prompt(task, task_title, attempt_context, attempt_count, student_first_name=None):
    """Build the user prompt for screenshot evaluation with context."""
    student_context = f"\n**Student name**: {student_first_name}" if student_first_name else ""

    # Extract task description (exclude starter code to avoid confusion)
    task_description = task.data
    if isinstance(task.data, dict):
        # For assignment_submission tasks with code field, only show the text description
        if 'text' in task.data:
            task_description = task.data['text']
        if 'code' in task.data:
            # Include starter code separately, clearly labeled
            starter_code = task.data['code']
            task_description += f"\n\n**Starter Code (draft provided to student - NOT their solution):**\n```python\n{starter_code}\n```"

    prompt = f"""Task Instructions: {task_description}

**Student submitted screenshot for assignment:** '{task_title}'

**IMPORTANT: The screenshot shows the student's ACTUAL CODE and output. The starter code above is just a DRAFT/TEMPLATE provided to the student - it is NOT their solution. Evaluate based on what you SEE in the screenshot, not the starter code.**{attempt_context}{student_context}

**Attempts: {attempt_count}**"""

    if attempt_count > 0:
        prompt += "\n\nIMPORTANT: Review previous submissions and feedback above. Do NOT repeat previous hints. Provide fresh perspective."

    prompt += "\n\nEvaluate if the screenshot demonstrates successful completion of the assignment. Provide brief, specific feedback."

    return prompt


def provide_screenshot_feedback(
    image_base64: str,
    mime_type: str,
    task: dict,
    language: str = "Russian",
    previous_attempts: list = None,
    student_first_name: str = None,
):
    """
    Provide AI-generated feedback for screenshot submission.

    This function evaluates screenshots (e.g., Python installation, VS Code setup, etc.)
    based on the task description provided, with support for attempt history and progressive feedback.

    Args:
        image_base64: Base64-encoded image data
        mime_type: MIME type of the image (e.g., 'image/png')
        task: Task object with description and title
        language: Language for feedback (English/Russian)
        previous_attempts: List of previous TaskAttempt objects for context
        student_first_name: Student's first name for personalization

    Returns:
        SubmissionGrader with feedback and is_solved status
    """
    language_instruction = get_language_instruction(language)

    # Extract task description and title
    task_description = task.data if isinstance(task.data, str) else str(task.data)
    task_title = task.task_name if hasattr(task, 'task_name') else "Assignment"

    # Build context from previous attempts if available
    attempt_context, attempt_count, failed_count = build_attempt_context(previous_attempts)

    # Build system prompt (similar to code evaluation)
    system_prompt = build_screenshot_system_prompt(
        language_instruction,
        task_description,
        task_title
    )

    # Build user prompt with context
    user_prompt = build_screenshot_user_prompt(
        task,
        task_title,
        attempt_context,
        attempt_count,
        student_first_name
    )

    # Call OpenAI Vision API with structured output
    completion = client.beta.chat.completions.parse(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}",
                            "detail": "low"  # Use low detail for faster/cheaper processing
                        }
                    }
                ]
            }
        ],
        response_format=SubmissionGrader,
    )

    result = completion.choices[0].message.parsed
    return result


def evaluate_screenshot_submission(image_base64, mime_type, task, language="Russian", previous_attempts=None, student_first_name=None):
    """
    Evaluate a screenshot submission for an assignment task.

    :param image_base64: Base64-encoded image data
    :param mime_type: MIME type of the image
    :param task: a task object
    :param language: language for AI feedback
    :param previous_attempts: list of previous TaskAttempt objects for context
    :param student_first_name: student's first name for personalization
    :return: SubmissionGrader with feedback and is_solved status
    """
    feedback = provide_screenshot_feedback(
        image_base64,
        mime_type,
        task,
        language,
        previous_attempts,
        student_first_name
    )
    return feedback
