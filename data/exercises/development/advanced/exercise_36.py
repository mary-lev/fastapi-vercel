# Test case for the function
def test_vigenere(text, key, expected):
    result = vigenere(text, key)
    if result == expected:
        return True
    else:
        return False


# Code of the function
def vigenere(text, key):
    result = list()

    a = "abcdefghijklmnopqrstuvwxyz"
    for idx, c in enumerate(text):
        if c in a:
            a_idx = a.index(c)
            k_idx = a.index(key[idx])
            result.append(a[(a_idx + k_idx) % len(a)])
        else:
            result.append(" ")

    return "".join(result)


# Tests
print(test_vigenere("attacking tonight", "oculorhinolaringo", "ovnlqbpvt eoeqtnh"))
print(test_vigenere("another exam", "bucainangolo", "bhqtprr klla"))
