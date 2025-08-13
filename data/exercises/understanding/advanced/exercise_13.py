def f(mat_string):
    c = 0
    lst = list()

    for chr in mat_string:
        n = int(chr)
        lst.append(n)
        if n / 2 != n // 2:
            c = c + 1

    return g(lst, c)


def g(mat_list, c):
    if c <= 0 or len(mat_list) == 0:
        return 0
    else:
        v = 0
        result = list()

        for i in mat_list:
            if v > 0:
                result.append(i)
            if i > 0 and v == 0:
                v = i

        return v + g(result, c - 1)


my_mat_string = input("Please provide ten 0-9 digits: ").strip()
print("Result:", f(my_mat_string))
