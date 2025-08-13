from collections import deque


# Test case for the function
def test_sequence(s, expected):
    result = sequence(s)
    if result == expected:
        return True
    else:
        return False


# Code of the function
def sequence(s):
    count = {}
    for c in s.lower():
        if c not in [".", ",", ";", " ", ":", "'"]:
            if c not in count:
                count[c] = 0
            count[c] += 1

    result = list()
    sorted_values = deque(sorted(count.values()))
    while len(sorted_values) > 0 and len(count) > 0:
        cur_count = sorted_values.pop()
        for c in s.lower():
            char_count = count.get(c)
            if char_count is not None and char_count == cur_count:
                result.append(c)
                del count[c]

    return "".join(result)


# Tests
print(
    test_sequence(
        "Alice was beginning to get very tired of sitting by her sister on the bank, and of having nothing to do",
        "niteogasrhbdvyflcwk",
    )
)
