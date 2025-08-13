# Test case for the function
def test_lev(a, b, expected):
    result = lev(a, b)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def lev(a, b):
    if a == "" or b == "":
        return 0
    elif a[0] == b[0]:
        return lev(a[1:], b[1:])
    else:
        lev_list = [lev(a[1:], b), lev(a, b[1:]), lev(a[1:], b[1:])]
        lev_list.sort()
        return 1 + lev_list[0]


# Tests
print(test_lev("hello", "hello", 0))
print(test_lev("", "hello", 0))
print(test_lev("hello", "", 0))
print(test_lev("", "", 0))
print(test_lev("hella", "hello", 1))
print(test_lev("this", "hello", 3))
print(test_lev("door", "beard", 3))
