# Test case for the function
def test_smc(a, b, expected):
    result = smc(a, b)
    if round(expected, 3) == round(result, 3):
        return True
    else:
        return False


# Code of the function
def smc(a, b):
    result = {(True, True): 0, (True, False): 0, (False, True): 0, (False, False): 0}

    for k in a:
        result[a[k], b[k]] += 1

    num = result[(True, True)] + result[(False, False)]
    den = num + result[(False, True)] + result[(True, False)]

    return num / den


# Tests
print(test_smc({"a": True, "b": True}, {"a": False, "b": False}, 0 / 2))
print(test_smc({"a": True, "b": True}, {"a": True, "b": True}, 2 / 2))
print(test_smc({"a": True, "b": False}, {"a": True, "b": True}, 1 / 2))
print(test_smc({"a": True, "b": False}, {"a": False, "b": False}, 1 / 2))
print(test_smc({"a": True, "b": False, "c": False}, {"a": False, "b": False, "c": False}, 2 / 3))
