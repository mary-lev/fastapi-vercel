# Test case for the function
def test_f(string, expected):
    result = f(string)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(string):
    return string + string


# Tests
print(test_f("mouse", "mousemouse"))
print(test_f("let me ", "let me let me "))
print(test_f("", ""))
