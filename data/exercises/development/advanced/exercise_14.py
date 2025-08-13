# Test case for the function
def test_caesar_cypher(msg, left_shift, shift_quantity, expected):
    result = caesar_cypher(msg, left_shift, shift_quantity)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def caesar_cypher(msg, left_shift, shift_quantity):
    result = list()
    alphabet = "abcdefghijklmnopqrstuvwxyz"

    if left_shift:
        shift_quantity = -shift_quantity
    cypher = alphabet[shift_quantity:] + alphabet[:shift_quantity]

    for c in msg.lower():
        if c in alphabet:
            result.append(cypher[alphabet.index(c)])
        else:
            result.append(c)

    return "".join(result)


# Tests
print(test_caesar_cypher("message to encrypt", True, 3, "jbppxdb ql bkzovmq"))
print(test_caesar_cypher("message to encrypt", False, 5, "rjxxflj yt jshwduy"))
