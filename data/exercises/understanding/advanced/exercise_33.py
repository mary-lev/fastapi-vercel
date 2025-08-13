from re import sub


def rsel(full_name, mat_string):
    uniq = []
    for c in full_name:
        if c not in uniq:
            uniq.append(c)

    r = []
    i = len(mat_string) // 2
    if i > 0:
        n = int(mat_string[i])
        if n < len(uniq):
            r.append(uniq[n])
            new_full_name = full_name[:n] + full_name[n + 1 :]
            new_mat_string = mat_string[:n] + mat_string[n + 1 :]
            r.extend(rsel(new_full_name, new_mat_string))

    return r


my_full_name = sub(" +", "", input("Please provide your full name: ").lower())
my_mat_string = sub(" +", " ", input("Please provide your matriculation number: ").lower())
print("Result:", rsel(my_full_name, my_mat_string))
