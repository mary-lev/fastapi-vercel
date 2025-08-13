def algorithm(cur_digit):
    result = None
    for digit in reversed(range(cur_digit)):
        if digit == cur_digit - 1:
            result = digit
        else:
            result = None
    return result


my_digit = int(input("Please provide an integer from 0 to 9: ").strip())
print("Result:", algorithm(my_digit))
