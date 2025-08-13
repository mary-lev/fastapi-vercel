def f(gn_list, fn_list, cur_number):
    all_numbers = list()
    for i in range(cur_number):
        if i < len(fn_list):
            all_numbers.append(i)

    idx = -1
    while True:
        idx = idx + 1
        if idx < len(gn_list):
            cur_char = gn_list[idx]
            for n in all_numbers:
                if cur_char == fn_list[n]:
                    return cur_char, n


my_gn = list(input("Please provide your given name: ").lower().replace(" ", "").strip())
my_fn = list(input("Please provide your family name: ").lower().replace(" ", "").strip())
my_nm = int(input("Please provide a number between 0 and 9: ").strip())
print("Result:", f(my_gn, my_fn, my_nm))
