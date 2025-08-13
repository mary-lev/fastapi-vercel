def r(gn, fn):
    g = ""
    f = None
    fl = list()
    for c in fn:
        fl.append(c)

    if len(fn) <= 1:
        return fn + gn
    else:
        for c in reversed(gn):
            if c >= fn[0]:
                g += c
            else:
                f = fn[1]
                g += f

        if f:
            fl.remove(f)
        else:
            fl.remove(fl[0])

        return r(g, "".join(fl))


my_gn = input("Please provide a given name: ").strip().lower()
my_fn = input("Please provide a family name: ").strip().lower()
print("Result:", r(my_gn, my_fn))
