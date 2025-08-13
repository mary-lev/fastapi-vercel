def f(mat, name):
    name_l = list(name)

    uni = set()
    for i in mat:
        if i < len(name):
            uni.add(i)

    if len(uni) % 2 > 0:
        uni.remove(0)

    sl = list()
    for i in uni:
        pos = 0
        for j in sl:
            if j < i:
                pos = pos + 1
        sl.insert(pos, i)

    sl_last = len(sl) - 1
    for i in range(len(sl) // 2):
        s = sl[i]
        e = sl[sl_last]
        tmp = name_l[s]
        name_l[s] = name_l[e]
        name_l[e] = tmp
        sl_last = sl_last - 1

    return "".join(name_l)


my_fn = input("Please provide your full name: ").strip().lower()
my_mat_l = [int(i) for i in input("Please provide your matriculation number: ").strip().strip("")]
print("Result:", f(my_mat_l, my_fn))
