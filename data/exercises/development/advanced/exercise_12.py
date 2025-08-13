# Test case for the function
def test_all_tokens_string_gen(tokens, expected):
    result = all_tokens_string_gen(tokens)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def all_tokens_string_gen(tokens):
    result = set()
    alfa_tokens = sorted(tokens)
    len_tokens = len(tokens)

    for idx in range(len_tokens):
        str_list = []
        for jdx in range(idx, len_tokens):
            str_list.append(alfa_tokens[jdx])
            result.add("".join(str_list))

    return result


# Tests
print(test_all_tokens_string_gen(["a"], {"a"}))
print(test_all_tokens_string_gen(["a", "b"], {"a", "b", "ab"}))
print(test_all_tokens_string_gen(["a", "c", "b"], {"a", "b", "c", "ab", "bc", "abc"}))
print(test_all_tokens_string_gen(["a", "c", "b", "d"], {"a", "b", "c", "d", "ab", "bc", "cd", "abc", "bcd", "abcd"}))
