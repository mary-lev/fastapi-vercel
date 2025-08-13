def f(x):
    r = 0
    x_len = len(x)
    while x_len > 0:
        r = r + x_len
        x_len = x_len - 1
    return r


print(f("me"))
