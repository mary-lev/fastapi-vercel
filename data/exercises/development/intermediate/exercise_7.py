# Test case for the function
def test_solve(n1, n2, n3, expected):
    result = solve(n1, n2, n3)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def solve(n1, n2, n3):
    for i in range(n1 + 1):
        for j in range(n2 + 1):
            for k in range(n3 + 1):
                if open_it((i, j, k)):
                    return i, j, k


# This variable and the related function is provided. The
# function checks if the combination in input opens the lock
combination = 8, 3, 6


def open_it(comb):
    return comb == combination


# Tests
print(test_solve(9, 9, 9, combination))
print(test_solve(8, 5, 9, combination))
print(test_solve(8, 3, 6, combination))
