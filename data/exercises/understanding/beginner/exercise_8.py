def ln(inp, val):
    for p, i in enumerate(inp):
        if i != val:
            return p


print(ln(["a", "b", "c"], "b"))
