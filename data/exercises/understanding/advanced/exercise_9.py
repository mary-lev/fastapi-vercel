def c(fn, mat):
    r = 0
    kind = 1
    for char in mat:
        r = r + (int(char) * kind)
        kind = kind * -1

    if r < 0:
        r = r * -1

    last = 0
    r = (r + 2) % len(fn)
    chars = list(fn)
    for idx in range(r):
        last = (last + idx) % r
        tmp = chars[idx]
        chars[idx] = chars[last]
        chars[last] = tmp

    return "".join(chars)


my_fn = input("Please provide a family name: ").strip().lower()
my_mn = input("Please provide ten 0-9 digits: ").strip()
print("Result:", c(my_fn, my_mn))
