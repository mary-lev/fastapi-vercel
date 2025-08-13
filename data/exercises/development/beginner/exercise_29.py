# Test case for the function
def test_f(s, t, expected):
    result = f(s, t)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(s, t):
    if s == t:
        return True
    elif len(s) == len(t):
        return False
    elif len(s) < len(t):
        return s
    else:
        return t


# Tests
print(test_f("ciao", "ciao", True))
print(test_f("ciao", "oaic", False))
print(test_f("ciao", "me", "me"))
print(test_f("me", "ciao", "me"))
