from re import sub


def prepare(s):
    n_list = list()

    support = ["9", "8", "7", "6", "5", "4", "3", "2", "1", "0"]

    for idx, c in enumerate(s):
        if c == "0" or c == "9":
            n_list.append(support[idx])
        else:
            n_list.append(c)

    return n_list


def s(n_list):
    list_r = list(range(len(n_list)))
    iters = list_r[1:]

    for iter in reversed(iters):
        for idx in range(iter):
            if n_list[idx] > n_list[idx + 1]:
                tmp = n_list[idx]
                n_list[idx] = n_list[idx + 1]
                n_list[idx + 1] = tmp

    return n_list


my_string_id = sub("\D", "", input("Please provide a string of ten 0-9 digits: "))
print("Result:", s(prepare(my_string_id)))
