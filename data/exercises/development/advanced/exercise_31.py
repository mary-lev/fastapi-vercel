# Test case for the function
def test_naive_ss(s, t, expected):
    result = naive_ss(s, t)
    if result == expected:
        return True
    else:
        return False


# Code of the function
def naive_ss(s, t):
    idx = 0
    s_len = len(s)
    t_len = len(t)

    while idx + s_len <= t_len:
        if s == t[idx : idx + s_len]:
            return idx, idx + s_len - 1
        idx = idx + 1

    return None


# Tests
print(test_naive_ss("aaa", "aaaaa", (0, 2)))
print(test_naive_ss("baa", "aababaa", (4, 6)))
print(test_naive_ss("bbb", "aaaaa", None))
