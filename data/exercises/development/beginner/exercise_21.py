# Test case for the function
def test_f(s1, s2, expected):
    result = f(s1, s2)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(s1, s2):
    result = set()

    for c in s1:
        if c in s2:
            result.add(c)

    return len(result)


# Tests
print(test_f("hello", "loch", 3))
print(test_f("hello", "hi", 1))
print(test_f("hello", "hello", 4))
print(test_f("hello", "try", 0))
