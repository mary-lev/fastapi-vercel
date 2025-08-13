def f(x, y, z):
    if x == y:
        return z[:x]
    else:
        return z[:y]


print(f(6, 3, "let it snow"))
