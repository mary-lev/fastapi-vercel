def f(s1, s2, n):
    if len(s1) > n and len(s2) > n:
        return s1[n] == s2[n]
    else:
        return len(s1) - len(s2)


print(f("donald", "duck", 4))
