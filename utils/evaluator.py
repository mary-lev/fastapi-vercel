
from .generator import provide_feedback


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