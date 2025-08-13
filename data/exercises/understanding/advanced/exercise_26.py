def izo(g_name, mat):
    result = set()

    for idx, d in enumerate(mat):
        if int(d) > 0:
            result.add(g_name[idx % len(g_name)])

    final = []
    for c in result:
        cur = 0
        for idx in range(len(final)):
            if c > final[idx]:
                cur = cur + 1
        final.insert(cur, c)

    return "".join(final)


my_mat = input("Please provide your matriculation number: ").strip()
my_given_name = input("Please provide your given name: ").strip().lower()
print("Result:", izo(my_given_name, my_mat))
