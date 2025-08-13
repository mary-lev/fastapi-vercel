from collections import deque


def cv(full_name, mat):
    result = dict()

    nq = deque()
    for d in mat:
        n = int(d)
        if n > 0:
            nq.append(int(n))

    vs = deque()
    idx = 0
    for c in full_name:
        if c in "aeiou":
            idx = idx + 1
            result[idx] = c
            if c not in vs:
                vs.append(c)

    while len(vs) != 0 and len(nq) != 0:
        e = vs.pop()
        i = nq.popleft()

        if i in result:
            result[i] = result[i] + e

    return result


my_full_name = input("Please provide your full name: ").strip().lower()
my_mat_string = input("Please provide your matriculation number: ").strip()
print("Result:", cv(my_full_name, my_mat_string))
