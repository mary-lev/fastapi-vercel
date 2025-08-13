# Test case for the function
def test_fib_dp(n, d, expected):
    result = fib_dp(n, d)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def fib_dp(n, d):
    # Checking if a solution exists
    if n not in d:
        if n <= 0:  # base case 1
            d[n] = 0
        elif n == 1:  # base case 2
            d[n] = 1
        else:  # recursive step
            # the dictionary will be passed as input of the recursive
            # calls of the function
            d[n] = fib_dp(n - 1, d) + fib_dp(n - 2, d)

    return d.get(n)


# Tests
print(test_fib_dp(0, dict(), 0))
print(test_fib_dp(1, dict(), 1))
print(test_fib_dp(2, dict(), 1))
print(test_fib_dp(7, dict(), 13))
