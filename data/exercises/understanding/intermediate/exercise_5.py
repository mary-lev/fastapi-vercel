def f(cur_digit):
    c_list = list()
    c_list.append("a")
    c_list.append("b")
    c_list.extend(c_list)
    c_list.extend(c_list)
    c_list.append("c")
    for i in range(cur_digit):
        if c_list[i] != "a" and "a" in c_list:
            c_list.remove("a")
        else:
            c_list.insert(i, "c")
    return c_list


my_digit = int(input("Please provide an integer number from 0 to 9: ").strip())
print("Result:", f(my_digit))
