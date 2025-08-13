# Test case for the function
def test_get_good_white_moves(white, black, expected):
    result = get_good_white_moves(white, black)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def get_good_white_moves(white, black):
    result = set(
        [
            (0, 0),
            (1, 0),
            (2, 0),
            (3, 0),
            (0, 1),
            (1, 1),
            (2, 1),
            (3, 1),
            (0, 2),
            (1, 2),
            (2, 2),
            (3, 2),
            (0, 3),
            (1, 3),
            (2, 3),
            (3, 3),
        ]
    )
    result.difference_update(white)
    result.difference_update(black)

    for x, y in set(result):
        if (
            not have_freedom((x - 1, y), black)
            and not have_freedom((x + 1, y), black)
            and not have_freedom((x, y - 1), black)
            and not have_freedom((x, y + 1), black)
        ):
            result.remove((x, y))

    return result


def have_freedom(t, black):
    return 0 <= t[0] <= 3 and 0 <= t[1] <= 3 and t not in black


# Tests
print(
    test_get_good_white_moves(
        {(1, 1), (0, 2), (0, 3), (1, 0)},
        {(2, 0), (2, 1), (3, 1), (2, 2), (2, 3)},
        {(0, 0), (0, 1), (1, 2), (1, 3), (3, 2), (3, 3)},
    )
)
