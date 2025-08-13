# Test case for the function
def test_xor(b1, b2, expected):
    result = xor(b1, b2)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def xor(b1, b2):
    return (b1 and not b2) or (not b1 and b2)


# Tests
print(test_xor(True, True, False))
print(test_xor(True, False, True))
print(test_xor(False, True, True))
print(test_xor(False, False, False))
