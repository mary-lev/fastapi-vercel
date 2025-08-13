from re import sub


def cou(mat, n_char):
    n_char_in_mat = n_char % len(mat)
    idx = int(mat[n_char_in_mat])

    mat_l = []
    for c in mat:
        mat_l.append(c)

    result = []
    while len(mat_l) > 0:
        jdx = idx % len(mat_l)
        result.append(mat_l[jdx])
        mat_l = mat_l[:jdx]

    return result


my_name = sub(" +", "", input("Please provide your name: ").lower())
my_mat = sub(" +", "", input("Please provide your matriculation number: ").lower())
print("Result:", cou(my_mat, len(my_name)))
