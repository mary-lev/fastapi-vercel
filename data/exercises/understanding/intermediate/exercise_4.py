def algorithm(a_list, pos):
    if pos >= len(a_list):
        return a_list
    else:
        common_division = pos / 2
        floor_division = pos // 2
        if floor_division < common_division:
            a_list.remove(a_list[floor_division])

        return algorithm(a_list, pos + 1)


my_list = [int(n) for n in input("Please provide ten 0-9 digits: ").strip()]
print("Result:", algorithm(my_list, 0))
