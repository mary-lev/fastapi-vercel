from collections import deque


def stack_from_list(input_list):
    output_stack = deque()  # the stack to create

    # Iterate each element in the input list and add it to the stack
    for item in input_list:
        output_stack.append(item)

    return output_stack
