# Test case for the function
def test_f(n1, n2, b, expected):
    result = f(n1, n2, b)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(n1, n2, b):
    if b:
        return n1 * n2
    else:
        return n1 // n2


# Tests
print(test_f(2, 3, True, 6))
print(test_f(2, 3, False, 0))
print(test_f(3, 3, True, 9))
print(test_f(3, 3, False, 1))
