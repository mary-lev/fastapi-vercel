def i(obj, x):
    if obj and x not in obj:
        return x
    else:
        return obj


print(i([], 6))
