from collections import deque
from re import sub


def f(nine_char):
    result = list()
    d = {0: list(), 1: list(), 2: list()}
    b = deque()
    idx = 0

    for c in nine_char:
        if c in ("a", "e", "i", "o", "u"):
            b.append("0")
        else:
            b.append("1")

    while len(b) != 0:
        idx = idx + 1
        for i in range(len(nine_char) // 3):
            d[i].append(b.pop())

    for i in range(idx):
        result.extend(d[i])

    return result


my_nine_char = sub("\s+", "", input("Please provide nine characters: "))[:9]
print("Result:", f(my_nine_char))
