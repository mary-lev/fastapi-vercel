from collections import deque


# Test case for the function
def test_do_it(string, number, expected):
    result = do_it(string, number)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def do_it(string, number):
    result = deque()

    for c in string:
        if c in "aeiou":
            result.append(c)

    if len(result) < number:
        return "Oh no!"
    else:
        return result


# Tests
print(test_do_it("just a string", 5, "Oh no!"))
print(test_do_it("just a string", 2, deque(["u", "a", "i"])))
