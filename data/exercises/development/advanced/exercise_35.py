# Test case for the function
def test_ic(s, c, expected):
    result = ic(s, c)
    # For testing it, I've approximated the result to integer
    if int(result) == int(expected):
        return True
    else:
        return False


# Code of the function
def ic(s, c):
    result = 0

    en_alphabeth = "abcdefghijklmnopqrstuvwxyz"
    s_len = 0
    for char in s:
        if char.lower() in en_alphabeth:
            s_len += 1

    for letter in en_alphabeth:
        letter_count = 0
        for char in s:
            if char.lower() == letter:
                letter_count += 1
            result += (letter_count / s_len) * ((letter_count - 1) / (s_len - 1))

    return c * result


# Tests
print(
    test_ic(
        "Alice was beginning to get very tired of sitting by her sister on the bank, and of having nothing to do",
        26,
        57,
    )
)
print(test_ic("This is another text in english", 26, 19))
