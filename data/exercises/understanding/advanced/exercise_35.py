from re import sub


def cnt(mat_string):
    result = 0

    if len(mat_string) > 0:
        n = int(mat_string[0])

        if n % 2 == 0:
            return 1 + cnt(mat_string[1:])
        else:
            return -1 + cnt(mat_string[1:])

    return result


my_mat_string = sub(" +", "", input("Please provide your matriculation number: ").lower())
print("Result:", cnt(my_mat_string))
