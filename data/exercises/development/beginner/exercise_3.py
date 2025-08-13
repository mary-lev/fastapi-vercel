# Test case for the function
def test_f(i1, i2, expected):
    result = f(i1, i2)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(i1, i2):
    return (i1 % 2) + (i2 % 2) == 0


# Tests
print(test_f(1, 3, False))
print(test_f(2, 3, False))
print(test_f(2, 4, True))
print(test_f(1, 4, False))
