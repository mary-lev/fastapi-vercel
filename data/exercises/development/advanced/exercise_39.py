# Test case for the function
def test_sd_coeff(s1, s2, expected):
    result = sd_coeff(s1, s2)
    if result is not None and (round(result, 2) == round(expected, 2)):
        return True
    else:
        return False


# Code of the function
def sd_coeff(s1, s2):
    count = 0
    for i in s1:
        if i in s2:
            count += 1

    den = len(s1) + len(s2)

    return (2 * count) / den


# Tests
print(test_sd_coeff({1, 2, 3}, {1, 2, 3}, 1.0))
print(test_sd_coeff({1, 2}, {1, 2, 3}, 0.8))
