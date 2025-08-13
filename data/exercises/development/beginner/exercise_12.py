# Test case for the function
def test_f(n1, n2, expected):
    result = f(n1, n2)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def f(n1, n2):
    n = n1 - n2
    if n < 0:
        n = -n
    return list(range(n))


# Tests
print(test_f(3, 4, [0]))
print(test_f(4, 2, [0, 1]))
print(test_f(9, 0, [0, 1, 2, 3, 4, 5, 6, 7, 8]))
