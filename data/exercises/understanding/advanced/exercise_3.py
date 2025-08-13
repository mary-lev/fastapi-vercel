def resolve(email, words):
    c_list = list()

    for idx in reversed(range(len(email))):
        c_list.append(email[idx])

    d = dict()
    for c in words:
        add(d, c)

    r = ""
    for i in c_list:
        if i not in d or not remove(d, i):
            r = r + i

    return r


def add(d, i):
    if i not in d:
        d[i] = 0
    d[i] = d[i] + 1


def remove(d, i):
    if i in d and d[i] > 0:
        d[i] = d[i] - 1
        return True

    return False


my_em = input("Please provide an email: ").strip()
my_gp = input("Please provide one or more words: ").strip()
print("Result:", resolve(my_em, my_gp))
