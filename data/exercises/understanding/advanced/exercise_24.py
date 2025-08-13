def r(f_name, m_list):
    f = list()

    for item in m_list:
        l_name = len(f_name)
        if item and l_name:
            idx = item % l_name
            f.extend(r(f_name[0:idx], m_list))
            f.insert(0, f_name[idx])
            return f

    return f


my_mat_list = [int(c) for c in input("Please provide your matriculation number: ").strip()]
my_full_string = input("Please provide your full name: ").strip().lower()
print("Result:", r(my_full_string, my_mat_list))
