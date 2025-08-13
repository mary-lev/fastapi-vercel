def f(n, s):
    if len(s) > n:
        return f(n, s[:n])
    else:
        return (n * 2) + 1


print(f(5, "Exams!"))
