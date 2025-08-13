# Test case for the function
def test_f(f1, f2, expected):
    result = f(f1, f2)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(f1, f2):
    return int(f1) + int(f2)


# Tests
print(test_f(12.3, 0.0, 12))
print(test_f(12.3, 7.9, 19))
print(test_f(1.1, 11.8, 12))
