from re import sub


def test(gn, fn, mn):
    result = 0

    c_gn = cnt(gn)
    c_fn = cnt(fn)

    for c in c_gn:
        if c in c_fn:
            result = result + (c_gn[c] - c_fn[c])

    idx = (len(gn) + len(fn)) % len(mn)
    return result * (int(mn[idx]) + 1)


def cnt(s):
    result = dict()

    for c in s:
        if c not in result:
            result[c] = 0
        result[c] = result[c] + 1

    return result


my_gn = sub("[^a-z]", "", input("Please provide a given name: ").strip().lower())
my_fn = sub("[^a-z]", "", input("Please provide a family name: ").strip().lower())
my_mn = input("Please provide ten 0-9 digits: ").strip()

print("Result:", test(my_gn, my_fn, my_mn))
