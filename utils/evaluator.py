
import os
import json
import random
import string
from enum import Enum
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field
from pydantic.class_validators import root_validator
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


client = OpenAI(api_key=OPENAI_API_KEY)

class SubmissionGrader(BaseModel):
    feedback: str
    is_solved: bool


def provide_feedback(
        answer: str,
        output: str,
        task: dict,
    ):

    system_prompt = f'''
        You are an AI assistant tasked with evaluating a student's Python code submission. 
        You will be provided with the task description and the student's answer. 
        Your job is to analyze the code, check for errors, and provide feedback.
        Please follow these steps to evaluate the student's answer:

        1. Carefully read the task description and the student's code.
        2. Analyze the code for syntax errors, logical errors, and any discrepancies between the task requirements and the implemented solution.
        3. Check if the code solves the given task correctly and efficiently.
        4. Look for any potential improvements or best practices that could be applied.
        After your analysis, provide feedback to the student that will help him or her to improve their coding skills. 
        Remember to be constructive and supportive in your feedback, focusing on helping the student.
        '''
    print(system_prompt)
    user_prompt = f'''
        Here is the task description: {task}.
        The student's answer is: {answer}
        Generate the feedback. Be polite and laconic.
        '''

    print(user_prompt)

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=SubmissionGrader,
        max_tokens=300,
    )
    result = completion.choices[0].message.parsed
    print(result.feedback)
    
    return result



def evaluate_code_submission(submission, output, task):
    """
    Evaluate a code submission for a task.
    :param submission: a code submission
    :param task: a task
    :return: a dictionary with the evaluation results
    """
    answer = submission['code']
    feedback = provide_feedback(answer, output, task)

    return feedback