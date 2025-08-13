from re import sub


def chk(name, mat):
    result = list()

    l_mat = len(mat)
    if l_mat > 0:
        max = l_mat // 2

        for idx in range(max):
            c = name[idx % len(name)]
            result.append(c)

        result.extend(chk(name, mat[:max]))

    return result


my_name = sub(" +", "", input("Please provide your name: ").lower())
my_mat = [int(n) for n in sub(" +", " ", input("Please provide your matriculation number: ").lower())]
print("Result:", chk(my_name, my_mat))
