# Test case for the function
def test_multiple_replace(s, c, r, o, expected):
    result = multiple_replace(s, c, r, o)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def multiple_replace(s, c, r, o):
    i_o = 0

    if o is None:
        o = len(s)

    for cur_c in s:
        if cur_c == c and i_o < o:
            s = s.replace(c, r[i_o % len(r)], 1)
            i_o += 1

    return s


# Tests
print(test_multiple_replace("mamma mia!", "m", ["n"], 3, "nanna mia!"))
print(test_multiple_replace("mamma mia!", "m", ["p", "l", "l"], 3, "palla mia!"))
print(test_multiple_replace("mamma mia!", "m", ["n", "s", "t"], None, "nasta nia!"))
