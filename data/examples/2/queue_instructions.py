from collections import deque  # import statement

my_first_queue = deque()  # this creates a new queue

my_first_queue.append("Vanessa Ives")  # these lines add two people
my_first_queue.append("Mike Wheeler")
# currently my_first_queue contains two items:
# deque(["Vanessa Ives", "Mike Wheeler")

my_first_queue.append("Eleven")  # add a new person
# now my_first_queue contains:
# deque(["Vanessa Ives", "Mike Wheeler", "Eleven"])

my_first_queue.popleft()  # it removes the first item added
# my_first_queue became:
# deque(["Mike Wheeler", "Eleven"])

my_second_queue = deque()  # this creates a new queue
my_second_queue.append("Michael Walsh")  # these lines add two people
my_second_queue.append("Lawrence Cohen")
# currently my_second_queue contains two items:
# deque(["Michael Walsh", "Lawrence Cohen"])

# add all the items in my_second_queue at the end of my_first_queue
my_first_queue.extend(my_second_queue)
# current status of my_first_queue:
# deque(["Mike Wheeler", "Eleven", "Michael Walsh", "Lawrence Cohen"])
