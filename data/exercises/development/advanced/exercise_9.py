# Test case for the function
def test_delta_decoding(l, expected):
    result = delta_decoding(l)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def delta_decoding(list_of_deltas):
    result = list()

    for idx, number in enumerate(list_of_deltas):
        result.append(number + sum(list_of_deltas[:idx]))

    return result


# Tests
print(test_delta_decoding([2, 2, 2, 3, -2], [2, 4, 6, 9, 7]))
print(test_delta_decoding([1, 1, 1, -1, -1], [1, 2, 3, 2, 1]))
print(test_delta_decoding([2, 2, 4, 8, 16], [2, 4, 8, 16, 32]))
