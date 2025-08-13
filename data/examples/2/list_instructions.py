my_first_list = list()  # this creates a new list

my_first_list.append(34)  # these two lines add two numbers
my_first_list.append(15)  # to the list in this precise order
# currently my_first_list contains two elements:
# list([ 34, 15 ])

# a list can contain items of any kind
my_first_list.append("Silvio")
# now my_first_list contains:
# list([34, 15, "Silvio"])

# it removes the first instance of the number 34
my_first_list.remove(34)
# my_first_list became:
# list([15, "Silvio"])

# it add again all the items in my_first_list to the list itself
my_first_list.extend(my_first_list)
# current status of my_first_list:
# list([15, "Silvio", 15, "Silvio"])

# it stores 4 in my_first_list_len
my_first_list_len = len(my_first_list)
