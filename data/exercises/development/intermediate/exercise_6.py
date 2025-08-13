from collections import deque


# Test case for the function
def test_pal(name, expected):
    result = pal(name)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def pal(name):
    if name == "":
        return name
    else:
        char = name[0]
        if char in ("a", "e", "i", "o", "u", "A", "E", "I", "O", "U"):
            char = ""
        return pal(name[1:]) + char


# Tests
print(test_pal("Silvio Peroni", "nrP vlS"))
print(test_pal("John Doé", "éD nhJ"))
print(test_pal("", ""))
