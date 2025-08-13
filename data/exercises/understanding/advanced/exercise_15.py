def f(email):
    user = email.split("@")[0]
    vowel = "aeiou"

    i = 0
    j = 0
    for c in user:
        if c not in ".0123456789":
            if c in vowel:
                i = i + 1
            else:
                j = j + 1

    if i < j:
        t = (i, j)
    else:
        t = (j, i)

    d = {"a": 0, "b": 0}
    for c in user.split(".")[1]:
        if c in vowel:
            d["a"] = d["a"] + t[1]
        else:
            d["b"] = d["b"] + t[0]

    return (d["a"], d["b"])


my_email = input("Please provide your institutional email: ").strip().lower()
print("Result:", f(my_email))
