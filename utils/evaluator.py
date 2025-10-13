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
    """Extract and format attempt history context."""
    if not previous_attempts:
        return "", 0, 0

    attempt_context = "\n\n**STUDENT'S LEARNING HISTORY**:\n"

    # Show up to 3 most recent previous attempts
    recent_attempts = previous_attempts[-3:] if len(previous_attempts) > 3 else previous_attempts

    for i, attempt in enumerate(recent_attempts, 1):
        attempt_status = "✓ Successful" if attempt.is_successful else "✗ Failed"
        code_preview = attempt.attempt_content[:150] if attempt.attempt_content else "[No code]"
        attempt_context += f"\nAttempt {attempt.attempt_number} [{attempt_status}]:\n{code_preview}...\n"

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

    base_instructions = """
SOCRATIC METHOD REQUIREMENTS:
You are a Socratic teacher who guides through questions, not answers.

CORE RULES:
1. NEVER provide working code or exact solutions
2. NEVER name the specific method they should use (like .count() or .lower())
3. Always respond with questions that lead to discovery
4. Use student's code as a starting point for inquiry

QUESTIONING PATTERNS BY ATTEMPT:
"""

    # Adjust questioning based on attempt count
    if attempt_count == 0:  # First attempt
        level = "- Broad questions: 'What are you trying to achieve?', 'What's the main goal?'\n"
        level += "- LIMIT: 1 sentence with 1-2 short questions maximum\n"
    elif attempt_count <= 2:  # Early attempts
        level = "- Focused questions: 'What does this method do?', 'Why this result?'\n"
        level += "- LIMIT: 1-2 sentences with 2-3 questions maximum\n"
    elif attempt_count <= 4:  # Middle attempts
        level = "- Narrower hints: 'What if you changed...?', 'What alternatives exist?'\n"
        level += "- LIMIT: 2-3 sentences with 3-4 questions maximum\n"
    else:  # Many attempts (struggling)
        level = "- Specific guidance: 'Try breaking the task into parts...', 'First solve the issue with...'\n"
        level += "- LIMIT: 3-4 sentences with 4-5 questions maximum\n"

    examples = """
EXAMPLE TRANSFORMATIONS:
DON'T: "Use .lower().count('substring')"
DO: "If all letters had the same case, would searching be easier?"

DON'T: "The .find() method returns an index, not a count"
DO: "What does 0 mean in the context of searching? Is it a count or something else?"

DON'T: "You need a for loop to count"
DO: "How can you go through all elements? What happens to each element?"
"""

    return base_instructions + level + "\n" + examples


def build_system_prompt(language_instruction, socratic_instructions, use_socratic):
    """Build the complete system prompt (always in English)."""
    if use_socratic:
        evaluation_section = """
Please follow these steps to evaluate the student's answer:
1. Carefully read the task description and the student's current code.
2. Review the student's previous attempts to understand their learning progression.
3. Determine if the code correctly solves the task (set is_solved accordingly).
4. If SOLVED: Congratulate the student and briefly explain what they did right.
5. If NOT SOLVED: Analyze misconceptions and craft guiding questions.
"""
        feedback_section = """
After your analysis, provide feedback based on solution status:

**IF THE CODE IS CORRECT (is_solved=true)**:
- Congratulate the student warmly
- Briefly explain what concept/technique they successfully applied
- IMPORTANT: Check the "Number of previous attempts" field:
  - If previous attempts = 0: This is their first success! Just congratulate the achievement.
  - If previous attempts > 0: Acknowledge their improvement/perseverance.
- Keep it concise (1-2 sentences)
- Examples:
  - First attempt: "Отлично, Мария! Вы правильно поняли, что строки неизменяемы, и присвоили результат обратно переменной."
  - After failed attempts: "Отлично, Мария! Теперь вы учли неизменяемость строк — отличная работа над ошибками!"

**IF THE CODE IS INCORRECT (is_solved=false)**:
- Use SOCRATIC questioning approach:
  - Ask guiding questions instead of providing answers
  - Help students discover their misconceptions through inquiry
  - Use "What if..." and "Why do you think..." patterns
  - Progressively narrow the scope based on attempt history
  - NEVER give the direct solution or exact method names
  - Follow the length limits based on attempt count
"""
    else:
        evaluation_section = """
Please follow these steps to evaluate the student's answer:
1. Carefully read the task description and the student's current code.
2. Review the student's previous attempts to understand their learning progression.
3. Analyze the code for syntax errors, logical errors, and any discrepancies.
4. Check if the code solves the given task correctly and efficiently.
5. Look for any potential improvements or best practices.
6. Consider the attempt history: Are they making progress? Repeating mistakes?
"""
        feedback_section = """
After your analysis, provide feedback that:
- Acknowledges their progress if they're improving from previous attempts
- Offers more specific hints if they're stuck (multiple failed attempts)
- Encourages persistence and learning from mistakes
- Guides them in the right direction without giving away the solution
- Is constructive, supportive, and personalized to their journey
"""

    return f"""You are an AI assistant tasked with evaluating a student's Python code submission.
You will be provided with the task description, the student's answer, and their previous attempts.
Your job is to analyze the code and provide contextual, progressive feedback.

{evaluation_section}

{socratic_instructions}

{feedback_section}

{language_instruction}

Remember: Students learn by struggling and overcoming challenges. Your feedback should help them discover the solution themselves."""


def build_user_prompt(task, answer, output, attempt_context, use_socratic, attempt_count, student_first_name=None):
    """Build the user prompt with appropriate instructions."""
    # Add student name context for gender-aware verb forms (especially important for Russian)
    student_context = ""
    if student_first_name:
        student_context = f"\n\n**Student's first name**: {student_first_name} (use this to infer gender for correct verb forms)"

    base_prompt = f"""Here is the task description: {task.data}.
The student's current answer is: {answer}
The output of the code is: {output}
{attempt_context}{student_context}

**Number of previous attempts: {attempt_count}**"""

    if use_socratic:
        guidance = "\n\nFirst, determine if the code correctly solves the task:\n"
        guidance += "- If CORRECT (is_solved=true): Congratulate the student in 1-2 sentences, explaining what they did right.\n"
        guidance += "  - ONLY mention 'progress' or 'improvement' if previous attempts > 0. Otherwise, just congratulate the achievement.\n"
        guidance += "- If INCORRECT (is_solved=false): "

        if attempt_count == 0:
            guidance += "Provide 1 brief sentence with 1-2 short questions that help the student think about the problem."
        elif attempt_count <= 2:
            guidance += "Provide 1-2 sentences with 2-3 questions that help them understand what their code is actually doing."
        elif attempt_count <= 4:
            guidance += "Provide 2-3 sentences with 3-4 questions about the gap between their approach and the solution."
        else:
            guidance += "Provide 3-4 sentences with 4-5 supportive questions that break down the problem into smaller steps."
    else:
        guidance = "\n\nGenerate the feedback. Be polite, laconic, and contextual.\nRespond in 1-2 sentences that acknowledge their journey and guide them forward."

    return base_prompt + guidance


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
