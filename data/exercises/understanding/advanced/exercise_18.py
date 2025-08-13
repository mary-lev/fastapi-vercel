def mir(family_name, mat_number):
    r = 0
    e = True
    for n in mat_number:
        if e:
            r = r + int(n)
            e = False
        else:
            r = r - int(n)
            e = True

    if r < 0:
        r = r * -1

    if r > 0 and family_name != "":
        idx = len(family_name) % r
        c = family_name[idx]
        return c + mir(family_name[1:-1], mat_number[1:-1]) + c
    else:
        return ""


my_family_name = input("Please provide your family name: ").strip().lower()
my_mat_number = input("Please provide your matriculation number: ").strip().lower()
print("Result:", mir(my_family_name, my_mat_number))
