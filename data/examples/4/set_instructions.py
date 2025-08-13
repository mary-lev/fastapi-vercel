my_first_set = set()  # this creates a new set

my_first_set.add(34)  # these two lines add two numbers
my_first_set.add(15)  # to the set without any particular order
# currently my_first_set contains two elements:
# set({ 34, 15 })

my_first_set.set("Silvio")  # a set can contains element of any kind
# now my_first_set contains:
# set({34, 15, "Silvio"})

my_first_set.remove(34)  # it removes the number 34
# my_first_set became:
# set({15, "Silvio"})

# it doesn't add the new elements since they are already included
my_first_set.update(my_first_set)
# current status of my_first_set:
# set({15, "Silvio"})

my_first_set_len = len(my_first_set)  # it stores 2 in my_first_set_len
