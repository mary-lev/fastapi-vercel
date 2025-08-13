from re import sub


def sc(chars, mat_list):
    n_op = []

    ln = len(mat_list)
    for idx in range(ln // 2):
        cur = mat_list[idx] + mat_list[ln - (1 + idx)]
        n_op.append(cur)

    result = set()
    for n in n_op:
        c = chars[n % len(chars)]
        result.add(c)

    return result


my_mat = list(input("Please provide your matriculation number: ").strip())
my_mat_list = [int(i) for i in my_mat]
my_chars = sub(" +", "", input("Please provide your full name: ").lower())
print("Result:", sc(my_chars, my_mat_list))
