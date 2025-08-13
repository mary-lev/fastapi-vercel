# Test case for the function
def test_alive_in_next_step(is_alive, neigh_alive, expected):
    result = alive_in_next_step(is_alive, neigh_alive)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def alive_in_next_step(is_alive, neigh_alive):
    rule_2 = is_alive and 2 <= len(neigh_alive) <= 3
    rule_4 = not is_alive and len(neigh_alive) == 3

    return rule_2 or rule_4


# Tests
print(test_alive_in_next_step(True, {1, 2}, True))
print(test_alive_in_next_step(True, {1, 2, 3, 4}, False))
print(test_alive_in_next_step(True, {1, 2, 3}, True))
print(test_alive_in_next_step(True, {1}, False))
print(test_alive_in_next_step(False, {1, 2}, False))
print(test_alive_in_next_step(False, {1, 2, 3, 4}, False))
print(test_alive_in_next_step(False, {1, 2, 3}, True))
print(test_alive_in_next_step(False, {1}, False))
