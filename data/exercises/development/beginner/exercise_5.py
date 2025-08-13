# Test case for the function
def test_f(s, n, expected):
    result = f(s, n)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(s, n):
    return s[n] in "aeiou"


# Tests
print(test_f("hello", 1, True))
print(test_f("hello", 3, False))
