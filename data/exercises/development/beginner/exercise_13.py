# Test case for the function
def test_f(s, b, expected):
    result = f(s, b)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(s, b):
    result = list()

    for c in s:
        if b and c in "aeiou":
            result.append(c)
        elif not b and c not in "aeiou":
            result.append(c)

    return result


# Tests
print(test_f("john doe", True, ["o", "o", "e"]))
print(test_f("john doe", False, ["j", "h", "n", " ", "d"]))
