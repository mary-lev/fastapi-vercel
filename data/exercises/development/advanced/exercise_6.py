# Test case for the function
def test_bigrams_jaccard(string_1, string_2, expected):
    result = bigrams_jaccard(string_1, string_2)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def bigrams_jaccard(string_1, string_2):
    bigrams_s1 = get_bigrams(string_1)
    bigrams_s2 = get_bigrams(string_2)

    return len(bigrams_s1.intersection(bigrams_s2)) / len(bigrams_s1.union(bigrams_s2))


def get_bigrams(s):
    result = set()

    for i in range(len(s) - 1):
        result.add(s[i] + s[i + 1])

    return result


# Tests
print(test_bigrams_jaccard("John Doe", "Jane Doe", 3 / 11))
print(test_bigrams_jaccard("John Doe", "John Doe", 7 / 7))
print(test_bigrams_jaccard("Jonathan Doe", "John Doe", 5 / 13))
