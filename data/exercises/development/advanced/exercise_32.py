from math import sqrt


# Test case for the function
def test_is_prime(n, expected):
    result = is_prime(n)
    if result is expected:
        return True
    else:
        return False


# Code of the function
def is_prime(n):
    d = 2

    while d <= sqrt(n):
        if n % d == 0:
            return False
        d += 1

    return True


# Tests
print(test_is_prime(1, True))
print(test_is_prime(2, True))
print(test_is_prime(3, True))
print(test_is_prime(4, False))
print(test_is_prime(5, True))
print(test_is_prime(6, False))
print(test_is_prime(17, True))
print(test_is_prime(22, False))
