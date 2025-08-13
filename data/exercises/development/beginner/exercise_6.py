# Test case for the function
def test_f(n, n_list, expected):
    result = f(n, n_list)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(n, n_list):
    result = 0
    for i in n_list:
        result += i
    return result == n


# Tests
print(test_f(10, [1, 2, 3, 4], True))
print(test_f(10, [0, 1, 2, 3, 4], True))
print(test_f(10, [1, 2, 3], False))
print(test_f(10, [1, 2, 3, 4, 5], False))
print(test_f(10, [], False))
