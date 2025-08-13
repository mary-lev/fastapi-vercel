from re import sub


def c_rec(chars, mat_list):
    result = ["a", "e", "i", "o", "u"]

    if len(mat_list) == 0:
        result = sorted(list(chars))
        return "".join(result)
    elif mat_list[0] % 2 == 0:
        idx = mat_list[0] % len(result)
        chars.add(result[idx])

    return c_rec(chars, mat_list[1:])


my_mat = list(input("Please provide your matriculation number: ").strip())
my_mat_list = [int(i) for i in my_mat]
my_chars = set(sub(" +", "", input("Please provide your full name: ").lower()))
print("Result:", c_rec(my_chars, my_mat_list))
