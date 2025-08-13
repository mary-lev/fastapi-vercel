# Immutable objects
my_num_1 = 41
my_num_2 = my_num_1
my_num_1 = my_num_1 + 1
print(my_num_1)  # 42
print(my_num_2)  # 41, since it is a copy of the original value

# Mutable objects
my_list_1 = list()
my_list_2 = my_list_1
my_list_1.append(1)
print(my_list_1)  # [1]
print(my_list_2)  # [1], since it points to the same list
