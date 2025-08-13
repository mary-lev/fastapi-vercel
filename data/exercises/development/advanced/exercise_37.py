# Test case for the function
def test_trial_div(n, expected):
    result = trial_div(n)
    if result == expected:
        return True
    else:
        return False


# Code of the function
def trial_div(n):
    result = []
    f = 2

    while not f > n:
        if n % f == 0:
            result.append(f)
            n = n / f
        else:
            f = f + 1

    return result


# Tests
print(test_trial_div(12, [2, 2, 3]))
print(test_trial_div(11, [11]))
print(test_trial_div(15, [3, 5]))
print(test_trial_div(18, [2, 3, 3]))
