# Test case for the function
def test_algorithm(dictionary, key_list, expected):
    result = algorithm(dictionary, key_list)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def algorithm(dictionary, key_list):
    result = set()

    for key in key_list:
        if key in dictionary:
            result.add(dictionary[key])

    return result


# Tests
print(test_algorithm({"a": 1, "b": 2, "c": 3}, ["a", "c"], {1, 3}))
print(test_algorithm({"a": 1, "b": 2, "c": 3}, ["d", "e"], set()))
print(test_algorithm({}, ["a", "c"], set()))
