def main(f_name, mat_number):
    f_name_l = list()
    for c in f_name:
        f_name_l.append(c)

    mat_number_l = list()
    for idx, n in enumerate(mat_number):
        mat_number_l.append((idx, int(n)))

    prep(f_name_l, mat_number_l)
    return r(f_name_l)


def prep(name_l, mat_l):
    l_len = len(name_l)
    for p1, p2 in mat_l:
        if p1 < l_len and p2 < l_len:
            tmp = name_l[p1]
            name_l[p1] = name_l[p2]
            name_l[p2] = tmp


def r(ipt):
    result = 0
    cur_len = len(ipt)
    if cur_len == 0:
        return result
    else:
        el = ipt[0]
        if el in "aeiou":
            result = cur_len
        return result + r(ipt[1:])


my_family_name = input("Please provide your family name: ").strip().lower()
my_mat_number = input("Please provide your matriculation number: ").strip().lower()
print("Result:", main(my_family_name, my_mat_number))
