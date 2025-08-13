# Test case for the function
def test_odd11(y, expected):
    result = odd11(y)
    if result == expected:
        return True
    else:
        return False


# Code of the function
def odd11(y):
    if y % 2 == 1:
        y = y + 11
    y = y / 2
    if y % 2 == 1:
        y = y + 11
    return 7 - (y % 7)


# Tests
print(test_odd11(0, 7))
print(test_odd11(3, 3))
print(test_odd11(42, 3))
print(test_odd11(7, 1))
