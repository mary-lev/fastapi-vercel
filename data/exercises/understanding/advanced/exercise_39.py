from re import sub


def t(given_name, mat_string):
    res = 0

    mat_len = len(mat_string)
    for i in range(mat_len):
        sx = int(mat_string[i])
        dx = int(mat_string[mat_len - i - 1])

        if sx < dx:
            n = dx - sx
        else:
            n = sx - dx

        res = res + n

    res_s = given_name[res % len(given_name)]
    res_b = res_s in "aeiou"

    return res_s, res_b


my_given_name = sub(" +", "", input("Please provide your given name: ")).lower()
my_mat_number = sub(" +", "", input("Please provide your matriculation number: ")).lower()
print("Result:", t(my_given_name, my_mat_number))
