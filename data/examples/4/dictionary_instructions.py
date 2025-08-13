my_first_dict = dict()  # this creates a new dictionary

# these following two lines add two pairs to the dictionary
my_first_dict["age"] = 34
my_first_dict["day of birth"] = 15
# currently my_first_dict contains two elements:
# dict({ "age": 34, "day of birth": 15 })

# a dictionary can contains even key-value pairs of different types
my_first_dict["name"] = "Silvio"
# now my_first_dict contains:
# dict({"age": 34, "day of birth": 15, "name": "Silvio"})

del my_first_dict["age"]  # it removes the pair with key "age"
# my_first_dict became:
# dict({"day of birth": 15, "name": "Silvio"})

my_first_dict.get("age")  # get the value associated to "age"
# the returned result will be None in this case

# the following lines create a new dictionary with two pairs
my_second_dict = dict()
my_second_dict["month of birth"] = 12
my_second_dict["day of birth"] = 28

# it adds a new pair to the current dictionary, and rewrite the value
# associated to the key "day of birth" with the one specified
my_first_dict.update(my_second_dict)
# current status of my_first_dict:
# dict({"day of birth": 28, "name": "Silvio", "month of birth": 12})

# it stores 3 in my_first_dict_len
my_first_dict_len = len(my_first_dict)
