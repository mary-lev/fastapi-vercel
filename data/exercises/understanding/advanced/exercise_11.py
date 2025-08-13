from re import sub


def rs(gn, fn, m, lst):
    if gn != "" and fn != "":
        if gn[0] < fn[0]:
            lst.append(int(m[0]))
        elif len(lst) > 1:
            v = lst[len(lst) - 1] * int(m[0])
            lst = lst[: len(lst) - 1] + [v]
        lst = rs(gn[1:], fn[1:], m[1:], lst)

    return lst


my_gn = sub("[^a-z]", "", input("Please provide a given name: ").strip().lower())
my_fn = sub("[^a-z]", "", input("Please provide a family name: ").strip().lower())
my_mn = input("Please provide ten 0-9 digits: ").strip()

print("Result:", rs(my_gn, my_fn, my_mn, list()))
