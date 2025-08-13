from collections import deque


def f(fn, mn):
    stack = deque()
    digits = list()

    for i in range(len(fn)):
        j = i % len(mn)
        digits.append(int(mn[len(mn) - 1 - j]))

    for idx, d in enumerate(reversed(digits)):
        if idx < (len(digits) / 2):
            stack.append((d, digits[idx]))

    result = list()
    for c in fn:
        result.append(c)

    while stack:
        t = stack.pop()
        if t[0] < len(fn) and t[1] < len(fn):
            tmp = fn[t[0]]
            result[t[0]] = fn[t[1]]
            result[t[1]] = tmp

    return "".join(result)


my_fn = input("Please provide a family name: ").strip().lower()
my_mn = input("Please provide ten 0-9 digits: ").strip()
print("Result:", f(my_fn, my_mn))
