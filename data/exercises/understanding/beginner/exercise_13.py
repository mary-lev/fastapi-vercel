def f(s):
    if len(s) > 3:
        return s[3:]
    else:
        return s[:3]


print(f("bod"))
