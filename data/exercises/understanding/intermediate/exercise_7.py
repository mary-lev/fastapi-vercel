from collections import deque
from re import sub


def f(str_name, str_email):
    result = deque()

    name_len = len(str_name)
    n = len(str_email.split("@")[0])
    if n // 2 >= name_len:
        n = name_len

    while n > 0:
        if n % 2 > 0:
            n = n - 1

        n = n // 2
        tmp = str_name[n]
        result.append(tmp)

    result.pop()

    return result


my_name = sub("\s+", " ", input("Please provide your full name: ")).strip()
my_email = sub("\s+", " ", input("Please provide your email: ")).strip()
print("Result:", f(" ".join(my_name), my_email))
