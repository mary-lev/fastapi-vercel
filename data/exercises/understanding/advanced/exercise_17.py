def fun(given_name, family_name, mat_number):
    n = len(given_name) - len(family_name)
    if n < 0:
        n = n * -1

    num_l = list()
    for idx, item in enumerate(mat_number):
        num_l.append(int(item) + idx + n)

    name_l = list()
    for c in given_name + family_name:
        if c != " ":
            name_l.append(c)

    result = list()
    name_len = len(name_l)
    for idx in num_l:
        c = name_l[idx % name_len]
        result.append(c)

    return result


my_given_name = input("Please provide your given name: ").strip().lower()
my_family_name = input("Please provide your family name: ").strip().lower()
my_mat_number = input("Please provide your matriculation number: ").strip().lower()
print("Result:", fun(my_given_name, my_family_name, my_mat_number))
