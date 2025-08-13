# Test case for the function
def test_f(x, y, expected):
    result = f(x, y)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(x, y):
    if x == y:
        return 0
    elif x % y == 0:
        return -1
    elif y % x == 0:
        return 1
    else:
        return None


# Tests
print(test_f(5, 5, 0))
print(test_f(5, 10, 1))
print(test_f(10, 5, -1))
print(test_f(5, 7, None))
