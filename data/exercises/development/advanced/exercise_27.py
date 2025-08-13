# Test case for the function
def test_qgpm(s, t, expected):
    result = qgpm(s, t)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def qgpm(s, t):
    common = 0
    t_list = list(t)

    for c in s:
        if c in t_list:
            common += 1
            t_list.remove(c)

    return (2 * common) / (len(s) + len(t))


# Tests
print(test_qgpm("ciao", "ciao", 1))
print(test_qgpm("mummy", "my", 4 / 7))
print(test_qgpm("m", "mummy", 2 / 6))
