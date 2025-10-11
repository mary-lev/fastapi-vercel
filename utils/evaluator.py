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
        return "IMPORTANT: Provide all feedback, explanations, and guidance in RUSSIAN language. Use proper Russian grammar and vocabulary appropriate for programming education."
    else:
        return "IMPORTANT: Provide all feedback, explanations, and guidance in ENGLISH language."


class SubmissionGrader(BaseModel):
    feedback: str
    is_solved: bool


def provide_code_feedback(
    answer: str,
    output: str,
    task: dict,
    language: str = "English",
):

    language_instruction = get_language_instruction(language)

    system_prompt = (
        f"{language_instruction}\n\n"
        "You are an AI assistant tasked with evaluating a student's Python code submission. "
        "You will be provided with the task description and the student's answer. "
        "Your job is to analyze the code, check for errors, and provide feedback. "
        "Please follow these steps to evaluate the student's answer:\n"
        "1. Carefully read the task description and the student's code.\n"
        "2. Analyze the code for syntax errors, logical errors, and any discrepancies between the task requirements and the implemented solution.\n"
        "3. Check if the code solves the given task correctly and efficiently.\n"
        "4. Look for any potential improvements or best practices that could be applied.\n"
        "After your analysis, provide feedback to the student that will help him or her to improve their coding skills. "
        "Avoid giving the direct solution but guide the student in the right direction. "
        "Remember to be constructive and supportive in your feedback, focusing on helping the student."
    )
    user_prompt = (
        f"Here is the task description: {task.data}.\n"
        f"The student's answer is: {answer}\n"
        f"The output of the code is: {output}\n"
        "Generate the feedback. Be polite and laconic."
        "Respond to student in one sentence."
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-5",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=SubmissionGrader,
        # max_tokens=300,
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
        model="gpt-5",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=SubmissionGrader,
        # max_tokens=300,
    )
    result = completion.choices[0].message.parsed

    return result


def evaluate_code_submission(submission, output, task, language="English"):
    """
    Evaluate a code submission for a task.
    :param submission: a code submission
    :param task: a task
    :param language: language for AI feedback
    :return: a dictionary with the evaluation results
    """
    answer = submission["code"]
    feedback = provide_code_feedback(answer, output, task, language)

    return feedback


def evaluate_text_submission(answer, task, language="English"):
    """
    Evaluate a text submission for a task.
    :param answer: a text submission
    :param task: a task
    :param language: language for AI feedback
    :return: a tuple with a boolean indicating correctness and a feedback message
    """
    feedback = provide_text_feedback(answer, task, language)
    return feedback
