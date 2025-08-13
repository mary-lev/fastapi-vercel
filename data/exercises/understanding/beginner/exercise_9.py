def f(name):
    result = set()
    for c in get_odd_numbers(name):
        result.add(name[c])
    return result


def get_odd_numbers(name):
    result = list()

    for n in range(len(name)):
        if n % 2 != 0:
            result.append(n)

    return result


print(f("Santa Claus"))
