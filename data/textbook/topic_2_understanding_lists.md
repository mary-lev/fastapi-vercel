A list is a mutable, or changeable, ordered sequence of elements. Each element or value that is inside of a list is called an item. Just as strings are defined as characters between quotes, lists are defined by having values between square brackets [ ].

A list of integers looks like this:

[-3, -2, -1, 0, 1, 2, 3]
A list of floats looks like this:

[3.14, 9.23, 111.11, 312.12, 1.05]
A list of strings:

['shark', 'cuttlefish', 'squid', 'mantis shrimp']
If we define our string list as sea_creatures:

sea_creatures = ['shark', 'cuttlefish', 'squid', 'mantis shrimp']
We can print them out by calling the variable:

print(sea_creatures)
And the output looks exactly like the list that we created:

Output
['shark', 'cuttlefish', 'squid', 'mantis shrimp']
Lists are a very flexible data type because they are mutable in that they can have values added, removed, and changed. There is a data type that is similar to lists but that can’t be changed, and that is called a tuple.

A list is a data structure in Python that is a mutable, or changeable, ordered sequence of elements. Each element or value that is inside of a list is called an item. Just as strings are defined as characters between quotes, lists are defined by having values between square brackets [ ].

Lists are great to use when you want to work with many related values. They enable you to keep data together that belongs together, condense your code, and perform the same methods and operations on multiple values at once.

When thinking about Python lists and other data structures that are types of collections, it is useful to consider all the different collections you have on your computer: your assortment of files, your song playlists, your browser bookmarks, your emails, the collection of videos you can access on a streaming service, and more.

Prerequisites
You should have Python 3 installed and a programming environment set up on your computer or server. If you don’t have a programming environment set up, you can refer to the installation and setup guides for a local programming environment or for a programming environment on your server appropriate for your operating system (Ubuntu, CentOS, Debian, etc.)

String Lists
To get started, let’s create a list that contains items of the string data type:

Info: To follow along with the example code in this tutorial, open a Python interactive shell on your local system by running the python3 command. Then you can copy, paste, or edit the examples by adding them after the >>> prompt.

sea_creatures = ['shark', 'cuttlefish', 'squid', 'mantis shrimp', 'anemone']
When we print out the list, the output responds exactly like the list we created:

print(sea_creatures)
Output
['shark', 'cuttlefish', 'squid', 'mantis shrimp', 'anemone']
As an ordered sequence of elements, each item in a list can be called individually, through indexing. Lists are a compound data type made up of smaller parts, and are very flexible because they can have values added, removed, and changed. When you need to store a lot of values or iterate over values, and you want to be able to readily modify those values, you’ll likely want to work with list data types.

In this tutorial, we’ll go through some of the ways that we can work with lists in Python.

Indexing Lists
Each item in a list corresponds to an index number, which is an integer value, starting with the index number 0.

For the list sea_creatures, the index breakdown looks like this:

‘shark’	‘cuttlefish’	‘squid’	‘mantis shrimp’	‘anemone’
0	1	2	3	4
The first item, the string 'shark' starts at index 0, and the list ends at index 4 with the item 'anemone'.

Because each item in a Python list has a corresponding index number, we’re able to access and manipulate lists in the same ways we can with other sequential data types.

Now we can call a discrete item of the list by referring to its index number:

print(sea_creatures[1])
Output
cuttlefish
The index numbers for this list range from 0-4, as shown in the table above. So to call any of the items individually, we would refer to the index numbers like this:

sea_creatures[0] = 'shark'
sea_creatures[1] = 'cuttlefish'
sea_creatures[2] = 'squid'
sea_creatures[3] = 'mantis shrimp'
sea_creatures[4] = 'anemone'
If we call the list sea_creatures with an index number of any that is greater than 4, it will be out of range as it will not be valid:

print(sea_creatures[18])
Output
IndexError: list index out of range
In addition to positive index numbers, we can also access items from the list with a negative index number, by counting backwards from the end of the list, starting at -1. This is especially useful if we have a long list and we want to pinpoint an item towards the end of a list.

For the same list sea_creatures, the negative index breakdown looks like this:

‘shark’	‘cuttlefish’	‘squid’	‘mantis shrimp’	‘anemone’
-5	-4	-3	-2	-1
So, if we would like to print out the item 'squid' by using its negative index number, we can do so like this:

print(sea_creatures[-3])
Output
squid
We can concatenate string items in a list with other strings using the + operator:

print('Sammy is a ' + sea_creatures[0])
Output
Sammy is a shark
We were able to concatenate the string item at index number 0 with the string 'Sammy is a '. We can also use the + operator to concatenate 2 or more lists together.

With index numbers that correspond to items within a list, we’re able to access each item of a list discretely and work with those items.

Modifying Items in Lists
We can use indexing to change items within the list, by setting an index number equal to a different value. This gives us greater control over lists as we are able to modify and update the items that they contain.

If we want to change the string value of the item at index 1 from 'cuttlefish' to 'octopus', we can do so like this:

sea_creatures[1] = 'octopus'
Now when we print sea_creatures, the list will be different:

print(sea_creatures)
Output
['shark', 'octopus', 'squid', 'mantis shrimp', 'anemone']
We can also change the value of an item by using a negative index number instead:

sea_creatures[-3] = 'blobfish'
print(sea_creatures)
Output
['shark', 'octopus', 'blobfish', 'mantis shrimp', 'anemone']
Now 'blobfish' has replaced 'squid' at the negative index number of -3 (which corresponds to the positive index number of 2).

Being able to modify items in lists gives us the ability to change and update lists in an efficient way.

Slicing Lists
We can also call out a few items from the list. Let’s say we would like to only print the middle items of sea_creatures, we can do so by creating a slice. With slices, we can call multiple values by creating a range of index numbers separated by a colon [x:y]:

print(sea_creatures[1:4])
Output
['octopus', 'blobfish', 'mantis shrimp']
When creating a slice, as in [1:4], the first index number is where the slice starts (inclusive), and the second index number is where the slice ends (exclusive), which is why in our example above the items at position, 1, 2, and 3 are the items that print out.

If we want to include either end of the list, we can omit one of the numbers in the list[x:y] syntax. For example, if we want to print the first 3 items of the list sea_creatures — which would be 'shark', 'octopus', 'blobfish' — we can do so by typing:

print(sea_creatures[:3])
Output
['shark', 'octopus', 'blobfish']
This printed the beginning of the list, stopping right before index 3.

To include all the items at the end of a list, we would reverse the syntax:

print(sea_creatures[2:])
Output
['blobfish', 'mantis shrimp', 'anemone']
We can also use negative index numbers when slicing lists, similar to positive index numbers:

print(sea_creatures[-4:-2])
print(sea_creatures[-3:])
Output
['octopus', 'blobfish']
['blobfish', 'mantis shrimp', 'anemone']
One last parameter that we can use with slicing is called stride, which refers to how many items to move forward after the first item is retrieved from the list. So far, we have omitted the stride parameter, and Python defaults to the stride of 1, so that every item between two index numbers is retrieved.

The syntax for this construction is list[x:y:z], with z referring to stride. Let’s make a larger list, then slice it, and give the stride a value of 2:

numbers = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

print(numbers[1:11:2])
Output
[1, 3, 5, 7, 9]
Our construction numbers[1:11:2] prints the values between index numbers inclusive of 1 and exclusive of 11, then the stride value of 2 tells the program to print out only every other item.

We can omit the first two parameters and use stride alone as a parameter with the syntax list[::z]:

print(numbers[::3])
Output
[0, 3, 6, 9, 12]
By printing out the list numbers with the stride set to 3, only every third item is printed:

0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12

Slicing lists with both positive and negative index numbers and indicating stride provides us with the control to manipulate lists and receive the output we’re trying to achieve.

Modifying Lists with Operators
Operators can be used to make modifications to lists. We’ll review using the + and * operators and their compound forms += and *=.

The + operator can be used to concatenate two or more lists together:

sea_creatures = ['shark', 'octopus', 'blobfish', 'mantis shrimp', 'anemone']
oceans = ['Pacific', 'Atlantic', 'Indian', 'Southern', 'Arctic']

print(sea_creatures + oceans)
Output
['shark', 'octopus', 'blobfish', 'mantis shrimp', 'anemone', 'Pacific', 'Atlantic', 'Indian', 'Southern', 'Arctic']
Because the + operator can concatenate, it can be used to add an item (or several) in list form to the end of another list. Remember to place the item in square brackets:

sea_creatures = sea_creatures + ['yeti crab']
print (sea_creatures)
Output
['shark', 'octopus', 'blobfish', 'mantis shrimp', 'anemone', 'yeti crab']
The * operator can be used to multiply lists. Perhaps you need to make copies of all the files in a directory onto a server, or share a playlist with friends — in these cases you would need to multiply collections of data.

Let’s multiply the sea_creatures list by 2 and the oceans list by 3:

print(sea_creatures * 2)
print(oceans * 3)
Output
['shark', 'octopus', 'blobfish', 'mantis shrimp', 'anemone', 'yeti crab', 'shark', 'octopus', 'blobfish', 'mantis shrimp', 'anemone', 'yeti crab']
['Pacific', 'Atlantic', 'Indian', 'Southern', 'Arctic', 'Pacific', 'Atlantic', 'Indian', 'Southern', 'Arctic', 'Pacific', 'Atlantic', 'Indian', 'Southern', 'Arctic']
By using the * operator we can replicate our lists by the number of times we specify.

We can also use compound forms of the + and * operators with the assignment operator =. The += and *= compound operators can be used to populate lists in a quick and automated way. You can use these operators to fill in lists with placeholders that you can modify at a later time with user-provided input, for example.

Let’s add an item in list form to the list sea_creatures. This item will act as a placeholder, and we’d like to add this placeholder item several times. To do this, we’ll use the += operator with a for loop.

for x in range(1,4):
    sea_creatures += ['fish']
    print(sea_creatures)
Output
['shark', 'octopus', 'blobfish', 'mantis shrimp', 'anemone', 'yeti crab', 'fish']
['shark', 'octopus', 'blobfish', 'mantis shrimp', 'anemone', 'yeti crab', 'fish', 'fish']
['shark', 'octopus', 'blobfish', 'mantis shrimp', 'anemone', 'yeti crab', 'fish', 'fish', 'fish']
For each iteration of the for loop, an extra list item of 'fish' is added to the original list sea_creatures.

The *= operator behaves in a similar way:

sharks = ['shark']

for x in range(1,4):
    sharks *= 2
    print(sharks)
Output
['shark', 'shark']
['shark', 'shark', 'shark', 'shark']
['shark', 'shark', 'shark', 'shark', 'shark', 'shark', 'shark', 'shark']
The operators + and * can be used to concatenate lists and multiply lists. The compound operators += and *= can concatenate lists and multiply lists and pass the new identity to the original list.

Removing an Item from a List
Items can be removed from lists by using the del statement. This will delete the value at the index number you specify within a list.

From the sea_creatures list, let’s remove the item 'octopus'. This item is located at the index position of 1. To remove the item, we’ll use the del statement then call the list variable and the index number of that item:

sea_creatures =['shark', 'octopus', 'blobfish', 'mantis shrimp', 'anemone', 'yeti crab']

del sea_creatures[1]
print(sea_creatures)
Output
['shark', 'blobfish', 'mantis shrimp', 'anemone', 'yeti crab']
Now the item at index position 1, the string 'octopus', is no longer in our list sea_creatures.

We can also specify a range with the del statement. Say we wanted to remove not only the item 'octopus', but also 'blobfish' and 'mantis shrimp' as well. We can call a range in sea_creatures with the del statement to accomplish this:

sea_creatures =['shark', 'octopus', 'blobfish', 'mantis shrimp', 'anemone', 'yeti crab']

del sea_creatures[1:4]
print(sea_creatures)
Output
['shark', 'anemone', 'yeti crab']
By using a range with the del statement, we were able to remove the items between the index number of 1 (inclusive), and the index number of 4 (exclusive), leaving us with a list of 3 items following the removal of 3 items.

The del statement allows us to remove specific items from the list data type.

Constructing a List with List Items
Lists can be defined with items that are made up of lists, with each bracketed list enclosed inside the larger brackets of the parent list:

sea_names = [['shark', 'octopus', 'squid', 'mantis shrimp'],['Sammy', 'Jesse', 'Drew', 'Jamie']]
These lists within lists are called nested lists.

To access an item within this list, we will have to use multiple indices:

print(sea_names[1][0])
print(sea_names[0][0])
Output
Sammy
shark
The first list, since it is equal to an item, will have the index number of 0, which will be the first number in the construction, and the second list will have the index number of 1. Within each inner nested list there will be separate index numbers, which we will call in the second index number:

sea_names[0][0] = 'shark'
sea_names[0][1] = 'octopus'
sea_names[0][2] = 'squid'
sea_names[0][3] = 'mantis shrimp'

sea_names[1][0] = 'Sammy'
sea_names[1][1] = 'Jesse'
sea_names[1][2] = 'Drew'
sea_names[1][3] = 'Jamie'
When working with lists of lists, it is important to keep in mind that you’ll need to refer to more than one index number in order to access specific items within the relevant nested list.

Conclusion
The list data type is a flexible data type that can be modified throughout the course of your program. This tutorial covered the basic features of lists, including indexing, slicing, modifying, and concatenating lists.