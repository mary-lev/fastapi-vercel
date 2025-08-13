# Test case for the function
def test_f(b, n, expected):
    result = f(b, n)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(b, n):
    return b and n % 2 == 0


# Tests
print(test_f(True, 3, False))
print(test_f(True, 4, True))
print(test_f(False, 3, False))
print(test_f(False, 4, False))
