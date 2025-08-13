# Test case for the function
def test_bubble_sort(value_list, expected):
    result = bubble_sort(value_list)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def bubble_sort(value_list):
    swap = True

    while swap:
        swap = False

        for idx in range(1, len(value_list)):
            if value_list[idx - 1] > value_list[idx]:
                swap = True
                tmp = value_list[idx]
                value_list[idx] = value_list[idx - 1]
                value_list[idx - 1] = tmp

    return value_list


# Tests
print(test_bubble_sort([], []))
print(test_bubble_sort([1], [1]))
print(test_bubble_sort([1, 2], [1, 2]))
print(test_bubble_sort([2, 1], [1, 2]))
print(test_bubble_sort([5, 2, 3, 6, 6], [2, 3, 5, 6, 6]))
print(test_bubble_sort([5, 2, 3, 6, 6, 1], [1, 2, 3, 5, 6, 6]))
