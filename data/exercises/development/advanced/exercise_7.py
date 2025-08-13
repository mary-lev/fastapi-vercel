# Test case for the function
def test_rabin_karp(s, p, expected):
    result = rabin_karp(s, p)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def rabin_karp(input, pattern):
    pattern_hash = hash(pattern)
    pattern_length = len(pattern)
    for idx in range(len(input) - pattern_length + 1):
        s_hash = hash(input[idx : idx + pattern_length])
        if pattern_hash == s_hash:
            return True
    return False


# Tests
print(test_rabin_karp("This is a simple string", "a si", True))
print(test_rabin_karp("This is a simple string", "solo", False))
print(test_rabin_karp("This is a simple string", "simple s", True))
