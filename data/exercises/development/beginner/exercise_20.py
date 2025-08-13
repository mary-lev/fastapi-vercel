# Test case for the function
def test_f(s, i, b, expected):
    result = f(s, i, b)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(s, i, b):
    if b:
        return s[i]
    else:
        return s[-1]


# Tests
print(test_f("hello", 0, True, "h"))
print(test_f("hello", 0, False, "o"))
print(test_f("hello", 2, True, "l"))
print(test_f("hello", 2, False, "o"))
