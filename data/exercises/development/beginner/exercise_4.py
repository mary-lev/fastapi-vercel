# Test case for the function
def test_f(s1, s2, expected):
    result = f(s1, s2)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(s1, s2):
    if len(s1) > len(s2):
        return -1
    elif len(s1) < len(s2):
        return 1
    else:
        return 0


# Tests
print(test_f("hello", "hi", -1))
print(test_f("hi", "hello", 1))
print(test_f("hello", "earth", 0))
