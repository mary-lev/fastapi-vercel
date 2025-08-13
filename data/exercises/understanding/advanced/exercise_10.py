def r_char(idx, c_str, c_set):
    cur_c = c_str[idx % len(c_str)]
    if cur_c in c_set:
        c_set.remove(cur_c)


def char_n(gn, fn, mn):
    result = 0

    gn_set = set(gn.replace(" ", ""))
    fn_set = set(fn.replace(" ", ""))

    rn = 0
    for n in mn:
        rn += int(n)

    r_char(rn, gn, gn_set)
    r_char(rn, fn, fn_set)

    n_set = gn_set.union(fn_set)
    for idx in range(len(n_set)):
        if str(idx) in mn:
            result = result + idx
        else:
            result = result - idx

    return result


my_gn = input("Please provide a given name: ").strip().lower()
my_fn = input("Please provide a family name: ").strip().lower()
my_mn = input("Please provide ten 0-9 digits: ").strip()

print("Result:", char_n(my_gn, my_fn, my_mn))
