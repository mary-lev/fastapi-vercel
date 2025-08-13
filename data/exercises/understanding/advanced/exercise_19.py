def f(last_name, mat):
    d = {}
    i = -1
    for c in last_name:
        if c not in d:
            i = i + 1
            d[i] = c

    if len(d) > 0:
        for n in mat:
            i = int(n) % len(d)
            return d[i] + f(last_name[1:], mat[1:])

    return "$"


my_family_name = input("Please provide your family name: ").strip()
my_mat_number = input("Please provide your matriculation number: ").strip()
print("Result:", f(my_family_name, my_mat_number))
