from re import sub


def cntc(given_name):
    d = dict()

    for c in given_name:
        if c not in d:
            d[c] = 1
        else:
            d[c] = d[c] + 1

    res = 0
    for i in d:
        if i in "aeiou":
            res = res + d[i]
        else:
            res = res + (d[i] * 2)

    return res


my_given_name = sub(" +", "", input("Please provide your given name: ")).lower()
print("Result:", cntc(my_given_name))
