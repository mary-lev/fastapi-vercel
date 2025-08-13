# Test case for the function
def test_hamming_distance(s1, s2, expected):
    result = hamming_distance(s1, s2)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def hamming_distance(s1, s2):
    if len(s1) < len(s2):
        return s1
    elif len(s1) > len(s2):
        return s2
    else:
        result = 0
        for i in range(len(s1)):
            if s1[i] != s2[i]:
                result = result + 1
        return result


# Tests
print(test_hamming_distance("Silvio", "Peroni", 6))
print(test_hamming_distance("Silvio", "Silvia", 1))
print(test_hamming_distance("Silvio", "Giovanni", "Silvio"))
print(test_hamming_distance("Silvio", "John", "John"))
