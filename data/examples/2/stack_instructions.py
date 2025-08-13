from collections import deque  # import statement

my_first_stack = deque()  # this creates a new stack

my_first_stack.append("Good Omens")  # these lines add two books
my_first_stack.append("Neverwhere")
# currently my_first_stack contains two items:
#        "Neverwhere"])
# deque(["Good Omens",

my_first_stack.append("The Name of the Rose")  # add a new book
# now my_first_stack contains:
#        "The Name of the Rose")]
#        "Neverwhere",
# deque(["Good Omens",

my_first_stack.pop()  # it removes the item on top of the stack
# my_first_stack became:
#        "Neverwhere"])
# deque(["Good Omens",

my_second_stack = deque()  # this creates a new stack
my_second_stack.append("American Gods")  # these lines add two books
my_second_stack.append("Fragile Things")
# currently my_second_stack contains two items:
#        "Fragile Things"])
# deque(["American Gods",

# it add all the items in my_second_stack on top of my_first_stack
my_first_stack.extend(my_second_stack)
# current status of my_first_stack:
#        "Fragile Things"])
#        "American Gods",
#        "Neverwhere",
# deque(["Good Omens",
