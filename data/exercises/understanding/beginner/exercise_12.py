def g(x):
    r = set()
    idx = 0
    for it in x:
        if it not in r:
            r.add(idx)
        idx = idx + 1
    return r


print(g([5, 7, 7, 2, 5, 7]))
