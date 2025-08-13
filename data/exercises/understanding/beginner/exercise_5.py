def f(s, n):
    if n < 0:
        return s
    else:
        return s + f(s, n - 1)


print(f("42", 1))
