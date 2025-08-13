# Test case for the function
def test_delta_encoding(l, expected):
    result = delta_encoding(l)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def delta_encoding(list_of_numbers):
    result = list()

    last = 0
    for number in list_of_numbers:
        result.append(number - last)
        last = number

    return result


# Tests
print(test_delta_encoding([2, 4, 6, 9, 7], [2, 2, 2, 3, -2]))
print(test_delta_encoding([1, 2, 3, 2, 1], [1, 1, 1, -1, -1]))
print(test_delta_encoding([2, 4, 8, 16, 32], [2, 2, 4, 8, 16]))
