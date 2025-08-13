# Test case for the algorithm
def test_multiplication(int_1, int_2, expected):
    result = multiplication(int_1, int_2)
    if expected == result:
        return True
    else:
        return False


# Code of the algorithm
def multiplication(int_1, int_2):
    if int_2 == 0:
        return 0
    else:
        return int_1 + multiplication(int_1, int_2 - 1)


print(test_multiplication(0, 0, 0))
print(test_multiplication(1, 0, 0))
print(test_multiplication(5, 7, 35))
