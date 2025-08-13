# Test case for the function
def test_glob(p, s, expected):
    result = glob(p, s)
    if result is expected:
        return True
    else:
        return False


# Code of the function
def glob(p, s):
    matches = p.split("*")

    for idx, pattern in enumerate(matches):
        if pattern in s:
            pos = s.index(pattern)

            if idx == len(matches) - 1 and pattern == "":
                new_start = len(s)
            elif idx > 0:
                new_start = pos + len(pattern)
            elif pos == 0:
                new_start = len(pattern)
            else:
                return False

            s = s[new_start:]
        else:
            return False

    return s == ""


# Tests
print(test_glob("*foo*", "foo", True))
print(test_glob("*foo*", "fidafoo", True))
print(test_glob("*foo*", "farfoofi", True))
print(test_glob("*foo*", "footer", True))
print(test_glob("*foo*", "fee", False))
print(test_glob("fee*", "fee", True))
print(test_glob("fee*", "feedoo", True))
print(test_glob("fee*", "fooee", False))
print(test_glob("*fae", "fae", True))
print(test_glob("*fae", "fafae", True))
print(test_glob("*fae", "fafaefa", False))
print(test_glob("*fae", "fee", False))
print(test_glob("doe", "doe", True))
print(test_glob("doe", "john doe", False))
print(test_glob("*pa*pe*", "paperino", True))
print(test_glob("*pa*foo*", "paparfoo", True))
print(test_glob("*pa*po*foo*", "papopaporfoo", True))
print(test_glob("*pa*foo*", "paparfoo", True))
