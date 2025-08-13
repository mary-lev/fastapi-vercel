# Test case for the function
def test_f(s, n, expected):
    result = f(s, n)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(s, n):
    return len(s) % n == 0


# Tests
print(test_f("good", 2, True))
print(test_f("hello", 2, False))
print(test_f("", 122, True))
