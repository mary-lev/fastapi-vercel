# Test case for the function
def test_sd(x, y, expected):
    result = sd(x, y)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def bigrams(s):
    bigram_list = list()
    bigram = ""

    for c in s:
        bigram += c
        if len(bigram) == 2:
            bigram_list.append(bigram)
            bigram = bigram[1:]

    return bigram_list


def sd(x, y):
    b1 = bigrams(x)
    b2 = bigrams(y)

    nt = 0
    for cur_b in b1:
        if cur_b in b2:
            nt += 1

    return (2 * nt) / (len(b1) + len(b2))


# Tests
print(test_sd("Finest", "Mine", 0.5))
print(test_sd("Finest", "Finest", 1.0))
