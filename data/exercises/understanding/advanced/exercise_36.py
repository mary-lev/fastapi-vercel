from re import sub


def do(five_chars):
    idx = 0

    alphabeth = list("abcdefghijklmnopqrstuvwxyz")
    for c in five_chars:
        if c in alphabeth:
            idx += alphabeth.index(c)
        else:
            idx -= 1

    result = set()
    idx = idx % 5
    for i in range(idx):
        result.add(five_chars[i])

    return result


my_five_char = sub(" +", "", input("Please provide the first five characters of your name: "))[:5]
print("Result:", do(my_five_char))
