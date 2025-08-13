from re import sub


def rin(g_name, f_name, idx):
    result = []

    if len(g_name) > 0:
        if g_name[0] in f_name:
            result.append(idx)

        idx = idx + 1
        result.extend(rin(g_name[1:], f_name, idx))

    return result


my_g_name = sub(" +", "", input("Please provide your given name: ").lower())
my_f_name = sub(" +", "", input("Please provide your family name: ").lower())
print("Result:", rin(my_g_name, my_f_name, 0))
