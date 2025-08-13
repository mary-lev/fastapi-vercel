# Test case for the function
def test_f(s, n, expected):
    result = f(s, n)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(s, n):
    return s[len(s) - 1] * n


# Tests
print(test_f("anna", 5, "aaaaa"))
print(test_f("ron", 3, "nnn"))
print(test_f("hermione", 0, ""))
