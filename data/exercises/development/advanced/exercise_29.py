from itertools import permutations
from random import randint


# Test case for the function
def test_fy(list_i, expected):
    result = fy(list_i)
    if tuple(result) in expected:
        return True
    else:
        return False


# Code of the function
def fy(s):
    list_s = list(s)
    for i in range(len(list_s) - 1):
        j = randint(i, len(list_s) - 1)

        tmp = list_s[i]
        list_s[i] = list_s[j]
        list_s[j] = tmp

    return "".join(list_s)


# Tests
print(test_fy([], permutations([])))
print(test_fy("a", permutations("a")))
print(test_fy("ab", permutations("ab")))
print(test_fy("abc", permutations("abc")))
