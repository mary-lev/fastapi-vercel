def f(s1, s2):
    result = True
    for c in s1:
        result = result and (c in s2)
    return result


print(f("riddle", "dialer"))
