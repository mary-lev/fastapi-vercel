# Test case for the function
def test_f(c, k, expected):
    result = f(c, k)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(c, k):
    return c * k


# Tests
print(test_f("a", 5, "aaaaa"))
print(test_f("b", 3, "bbb"))
print(test_f("c", 0, ""))
