def f(mat_list, n_odd):
    if n_odd <= 0 or len(mat_list) == 0:
        return 0
    else:
        v = 0
        result = list()

        for i in mat_list:
            if v > 0:
                result.append(i)
            if i > 0 and v == 0:
                v = i

        return v + f(result, n_odd - 1)


my_mat_list = [int(i) for i in input("Please provide 10 0-9 digits: ").strip()]
my_n_odd = sum([1 for n in my_mat_list if n % 2 != 0])
print("Result:", f(my_mat_list, my_n_odd))
