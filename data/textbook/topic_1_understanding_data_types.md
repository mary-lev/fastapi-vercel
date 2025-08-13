In Python, like in all programming languages, data types are used to classify one particular type of data. This is important because the specific data type you use will determine what values you can assign to it and what you can do to it (including what operations you can perform on it).

In this tutorial, we will go over the important data types native to Python. This is not an exhaustive investigation of data types, but will help you become familiar with what options you have available to you in Python.

Prerequisites
You should have Python 3 installed and a programming environment set up on your computer or server. If you don’t have a programming environment set up, you can refer to the installation and setup guides for a local programming environment or for a programming environment on your server appropriate for your operating system (Ubuntu, CentOS, Debian, etc.)

Background
One way to think about data types is to consider the different types of data that we use in the real world. An example of data in the real world are numbers: we may use whole numbers (0, 1, 2, …), integers (…, -1, 0, 1, …), and irrational numbers (π), for example.

Usually, in math, we can combine numbers from different types, and get some kind of an answer. We may want to add 5 to π, for example:

5 + π
We can either keep the equation as the answer to account for the irrational number, or round π to a number with a brief number of decimal places, and then add the numbers together:

5 + π = 5 + 3.14 = 8.14 
But, if we start to try to evaluate numbers with another data type, such as words, things start to make less sense. How would we solve for the following equation?

sky + 8
For computers, each data type can be thought of as being quite different, like words and numbers, so we will have to be careful about how we use them to assign values and how we manipulate them through operations.

Numbers
Any number you enter in Python will be interpreted as a number; you are not required to declare what kind of data type you are entering. Python will consider any number written without decimals as an integer (as in 138) and any number written with decimals as a float (as in 138.0).

Integers
Like in math, integers in computer programming are whole numbers that can be positive, negative, or 0 (…, -1, 0, 1, …). An integer can also be known as an int. As with other programming languages, you should not use commas in numbers of four digits or more, so when you write 1,000 in your program, write it as 1000.

Info: To follow along with the example code in this tutorial, open a Python interactive shell on your local system by running the python3 command. Then you can copy, paste, or edit the examples by adding them after the >>> prompt.

We can print out an integer like this:

print(-25)
Output
-25
Or, we can declare a variable, which in this case is essentially a symbol of the number we are using or manipulating, like so:

my_int = -25
print(my_int)
Output
-25
We can do math with integers in Python, too:

int_ans = 116 - 68
print(int_ans)
Output
48
Integers can be used in many ways within Python programs, and as you continue to learn more about the language you will have a lot of opportunities to work with integers and understand more about this data type.

Floating-Point Numbers
A floating-point number or a float is a real number, meaning that it can be either a rational or an irrational number. Because of this, floating-point numbers can be numbers that can contain a fractional part, such as 9.0 or -116.42. In general, for the purposes of thinking of a float in a Python program, it is a number that contains a decimal point.

Like we did with the integer, we can print out a floating-point number like this:

print(17.3)
Output
17.3
We can also declare a variable that stands in for a float, like so:

my_flt = 17.3
print(my_flt)
Output
17.3
And, just like with integers, we can do math with floats in Python, too:

flt_ans = 564.0 + 365.24
print(flt_ans)
Output
929.24
With integers and floating-point numbers, it is important to keep in mind that 3 ≠ 3.0, as 3 refers to an integer while 3.0 refers to a float.

Booleans
The Boolean data type can be one of two values, either True or False. Booleans are used to represent the truth values that are associated with the logic branch of mathematics, which informs algorithms in computer science.

Whenever you see the data type Boolean, it will start with a capitalized B because it is named for the mathematician George Boole. The values True and False will also always be with a capital T and F respectively, as they are special values in Python.

Many operations in math give us answers that evaluate to either True or False:

greater than
500 > 100 True
1 > 5 False
less than
200 < 400 True
4 < 2 False
equal
5 = 5 True
500 = 400 False
Like with numbers, we can store a Boolean value in a variable:

my_bool = 5 > 8
We can then print the Boolean value with a call to the print() function:

print(my_bool)
Since 5 is not greater than 8, we will receive the following output:

Output
False
As you write more programs in Python, you will become more familiar with how Booleans work and how different functions and operations evaluating to either True or False can change the course of the program.

Strings
A string is a sequence of one or more characters (letters, numbers, symbols) that can be either a constant or a variable. Strings exist within either single quotes ' or double quotes " in Python, so to create a string, enclose a sequence of characters in quotes:

'This is a string in single quotes.'
"This is a string in double quotes."
You can choose to use either single quotes or double quotes, but whichever you decide on you should be consistent within a program.

The basic program “Hello, World!” demonstrates how a string can be used in computer programming, as the characters that make up the phrase Hello, World! are a string.

print("Hello, World!")
As with other data types, we can store strings in variables:

hw = "Hello, World!"
And print out the string by calling the variable:

print(hw)
Ouput
Hello, World!
Like numbers, there are many operations that we can perform on strings within our programs in order to manipulate them to achieve the results we are seeking. Strings are important for communicating information to the user, and for the user to communicate information back to the program.