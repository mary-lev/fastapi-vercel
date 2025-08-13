from re import sub


def sstr(family_name):
    if len(family_name) > 1:
        m = len(family_name) // 2
        l_name = family_name[0:m]
        r_name = family_name[m : len(family_name)]
        return sstr(l_name) + sstr(r_name)

    r = -1
    v = "aeiou"
    for idx, c in enumerate(v):
        if family_name == c:
            r = idx

    return r


my_family_name = sub(" +", "", input("Please provide your family name: ").lower())
print("Result:", sstr(my_family_name))
