from collections import deque


def f(s1, s2):
    l = list()
    indexes = deque(range(len(s1)))
    while len(indexes) > 0:
        idx = indexes.popleft()
        if idx < len(s2):
            l.append(s2[idx])
        else:
            l.append(s1[idx])
    return "".join(l)


print(f("big", "brother"))
