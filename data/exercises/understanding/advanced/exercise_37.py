from re import sub
from collections import deque


def first(mat_string, given_name):
    s = deque()

    for char in mat_string:
        n = int(char)
        if n > 0:
            s.append(n)

    return second(s, given_name)


def second(c, gn):
    if len(c) == 0:
        return 0
    else:
        i = c.pop()
        s = gn[(i - 1) % len(gn)]
        if s in "aeiou":
            return 2 + second(c, gn)
        else:
            return -1 + second(c, gn)


my_given_name = sub(" +", "", input("Please provide your given name: ")).lower()
my_mat_string = sub(" +", "", input("Please provide a 10-digit matriculation string: "))
print("Result:", first(my_mat_string, my_given_name))
