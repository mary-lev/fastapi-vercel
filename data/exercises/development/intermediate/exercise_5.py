from collections import deque


# Test case for the function
def test_do_it(queue, number, expected):
    result = do_it(queue, number)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def do_it(queue, number):
    if number <= len(queue):
        for i in range(number):
            queue.popleft()
        return queue


# Tests
print(test_do_it(deque(["a", "b"]), 3, None))
print(test_do_it(deque(["a", "b", "c", "d", "e"]), 3, deque(["d", "e"])))
