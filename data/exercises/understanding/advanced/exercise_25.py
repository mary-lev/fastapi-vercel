def n(f_name, mat):
    chars = []
    first = ""

    for sn in mat:
        if first == "":
            first = sn
        i = int(sn)
        cur = f_name[i % len(mat)]
        chars.append(cur)

    result = "".join(chars)
    if result != "":
        return result[0] + n(result, mat.replace(first, ""))
    else:
        return ""


my_mat = input("Please provide your matriculation number: ").strip()
my_full_name = input("Please provide your full name: ").strip().lower()
print("Result:", n(my_full_name, my_mat))
