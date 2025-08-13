# Test case for the algorithm
def test_insertion_sort(input_list, expected):
    result = insertion_sort(input_list)
    if expected == result:
        return True
    else:
        return False


# Code of the algorithm
def insertion_sort(input_list):
    result = list()  # A new empty list where to store the result

    # iterate all the items on the input list
    for item in input_list:

        # initialise the position where to insert the item at the end of the result list
        insert_position = len(result)

        # iterate, in reverse order, all the positions of all the items already included in the result list
        for prev_position in reversed(range(insert_position)):

            # check if the current item is less than the one in prev_position in the result list
            if item < result[prev_position]:
                # if it is so, then the position where to insert the current item becomes prev_position
                insert_position = prev_position

        # the item is inserted into the position found
        result.insert(insert_position, item)

    return result  # the ordered list is returned


number_list = [3, 4, 1, 2, 9, 2]
number_sorted = [1, 2, 2, 3, 4, 9]
number_sorted_reversed = [9, 4, 3, 2, 2, 1]
print(test_insertion_sort(number_list, number_sorted))
print(test_insertion_sort(number_sorted, number_sorted))
print(test_insertion_sort(number_sorted_reversed, number_sorted))

book_list = ["Coraline", "American Gods", "The Graveyard Book", "Good Omens", "Neverwhere"]
book_list_sorted = ["American Gods", "Coraline", "Good Omens", "Neverwhere", "The Graveyard Book"]
book_list_reversed = ["The Graveyard Book", "Neverwhere", "Good Omens", "Coraline", "American Gods"]
print(test_insertion_sort(book_list, book_list_sorted))
print(test_insertion_sort(book_list_sorted, book_list_sorted))
print(test_insertion_sort(book_list_reversed, book_list_sorted))
