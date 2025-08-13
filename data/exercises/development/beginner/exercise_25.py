# Test case for the function
def test_f(s, n, expected):
    result = f(s, n)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(s, n):
    if n < len(s):
        return s[n]
    else:
        return None


# Tests
print(test_f("ciao", 4, None))
print(test_f("ciao", 0, "c"))
print(test_f("ciao", 2, "a"))
print(test_f("ciao", 7, None))
