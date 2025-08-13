# Test case for the function
def test_rolling_hash(s, a, expected):
    result = rolling_hash(s, a)
    if result == expected:
        return True
    else:
        return False


# Code of the function
def rolling_hash(s, a):
    r = 0
    n = len(s)

    for i, c in enumerate(s):
        r += ord(c) * a ** (n - (i + 1))

    return r


# Tests
print(test_rolling_hash("ciao", 1, 412))
print(test_rolling_hash("ciao", 2, 1517))
print(test_rolling_hash("ciao", 3, 4020))
