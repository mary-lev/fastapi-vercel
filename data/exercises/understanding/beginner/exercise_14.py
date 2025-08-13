def f(n):
    result = list()
    while n > 0:
        result.append(n)
        n = n - 1
    return len(result)


print(f(3))
