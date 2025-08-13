# Test case for the algorithm
def test_fib_dc(n, expected):
    result = fib_dc(n)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def fib_dc(n):
    if n <= 0:  # base case 1
        return 0
    if n == 1:  # base case 2
        return 1
    else:  # recursive step
        return fib_dc(n - 1) + fib_dc(n - 2)


# Tests
print(test_fib_dc(0, 0))
print(test_fib_dc(1, 1))
print(test_fib_dc(2, 1))
print(test_fib_dc(7, 13))
