The Python programming language comes with a variety of built-in functions. Among these are several common functions, including:

print() which prints expressions out
abs() which returns the absolute value of a number
int() which converts another data type to an integer
len() which returns the length of a sequence or collection
These built-in functions, however, are limited, and we can make use of modules to make more sophisticated programs.

Modules are Python .py files that consist of Python code. Any Python file can be referenced as a module. A Python file called hello.py has the module name of hello that can be imported into other Python files or used on the Python command line interpreter. You can learn about creating your own modules by reading How To Write Modules in Python 3.

Modules can define functions, classes, and variables that you can reference in other Python .py files or via the Python command line interpreter.

In Python, modules are accessed by using the import statement. When you do this, you execute the code of the module, keeping the scopes of the definitions so that your current file(s) can make use of these.

When Python imports a module called hello for example, the interpreter will first search for a built-in module called hello. If a built-in module is not found, the Python interpreter will then search for a file named hello.py in a list of directories that it receives from the sys.path variable.

This tutorial will walk you through checking for and installing modules, importing modules, and aliasing modules.

Prerequisites
You should have Python 3 installed and a programming environment set up on your computer or server. If you don’t have a programming environment set up, you can refer to the installation and setup guides for a local programming environment or for a programming environment on your server appropriate for your operating system (Ubuntu, CentOS, Debian, etc.)

Checking For and Installing Modules
There are a number of modules that are built into the Python Standard Library, which contains many modules that provide access to system functionality or provide standardized solutions. The Python Standard Library is part of every Python installation.

Info: To follow along with the example code in this tutorial, open a Python interactive shell on your local system by running the python3 command. Then you can copy, paste, or edit the examples by adding them after the >>> prompt.

To check that these Python modules are ready to go, enter into your local Python 3 programming environment or server-based programming environment and start the Python interpreter in your command line like so:

python
From within the interpreter you can run the import statement to make sure that the given module is ready to be called, as in:

import math
Since math is a built-in module, your interpreter should complete the task with no feedback, returning to the prompt. This means you don’t need to do anything to start using the math module.

Let’s run the import statement with a module that you may not have installed, like the 2D plotting library matplotlib:

import matplotlib
If matplotlib is not installed, you’ll receive an error like this:

Output
ImportError: No module named 'matplotlib'
You can deactivate the Python interpreter with CTRL + D and then install matplotlib with pip.

Next, we can use pip to install the matplotlib module:

pip install matplotlib
Once it is installed, you can import matplotlib in the Python interpreter using import matplotlib, and it will complete without error.

Importing Modules
To make use of the functions in a module, you’ll need to import the module with an import statement.

An import statement is made up of the import keyword along with the name of the module.

In a Python file, this will be declared at the top of the code, under any shebang lines or general comments.

So, in the Python program file my_rand_int.py we would import the random module to generate random numbers in this manner:

my_rand_int.py
import random
When we import a module, we are making it available to us in our current program as a separate namespace. This means that we will have to refer to the function in dot notation, as in [module].[function].

In practice, with the example of the random module, this may look like a function such as:

random.randint() which calls the function to return a random integer, or
random.randrange() which calls the function to return a random element from a specified range.
Let’s create a for loop to show how we will call a function of the random module within our my_rand_int.py program:

my_rand_int.py
import random


for i in range(10):
    print(random.randint(1, 25))
This small program first imports the random module on the first line, then moves into a for loop which will be working with 10 elements. Within the loop, the program will print a random integer within the range of 1 through 25 (inclusive). The integers 1 and 25 are passed to random.randint() as its parameters.

When we run the program with python my_rand_int.py, we’ll receive 10 random integers as output. Because these are random you’ll likely get different integers each time you run the program, but they’ll generate something like this:

Output
6
9
1
14
3
22
10
1
15
9
The integers should never go below 1 or above 25.

If you would like to use functions from more than one module, you can do so by adding multiple import statements:

my_rand_int.py
import random
import math
You may see programs that import multiple modules with commas separating them — as in import random, math — but this is not consistent with the PEP 8 Style Guide.

To make use of our additional module, we can add the constant pi from math to our program, and decrease the number of random integers printed out:

my_rand_int.py
import random
import math


for i in range(5):
    print(random.randint(1, 25))

print(math.pi)
Now, when we run our program, we’ll receive output that looks like this, with an approximation of pi as our last line of output:

Output
18
10
7
13
10
3.141592653589793
The import statement allows you to import one or more modules into your Python program, letting you make use of the definitions constructed in those modules.

Using from … import
To refer to items from a module within your program’s namespace, you can use the from … import statement. When you import modules this way, you can refer to the functions by name rather than through dot notation

In this construction, you can specify which definitions to reference directly.

In other programs, you may see the import statement take in references to everything defined within the module by using an asterisk (*) as a wildcard, but this is discouraged by PEP 8.

Let’s first review at importing one specific function, randint() from the random module:

my_rand_int.py
from random import randint
Here, we first call the from keyword, then random for the module. Next, we use the import keyword and call the specific function we would like to use.

Now, when we implement this function within our program, we will no longer write the function in dot notation as random.randint() but instead will only write randint():

my_rand_int.py
from random import randint


for i in range(10):
    print(randint(1, 25))
When you run the program, you’ll receive output similar to what we received earlier.

Using the from … import construction allows us to reference the defined elements of a module within our program’s namespace, letting us avoid dot notation.

Aliasing Modules
It is possible to modify the names of modules and their functions within Python by using the as keyword.

You may want to change a name because you have already used the same name for something else in your program, another module you have imported also uses that name, or you may want to abbreviate a longer name that you are using a lot.

The construction of this statement looks like the following:

import [module] as [another_name]
Let’s modify the name of the math module in our my_math.py program file. We’ll change the module name of math to m in order to abbreviate it. Our modified program will look like this:

my_math.py
import math as m


print(m.pi)
print(m.e)
Within the program, we now refer to the pi constant as m.pi rather than math.pi.

For some modules, it is commonplace to use aliases. The matplotlib.pyplot module’s official documentation calls for use of plt as an alias:

import matplotlib.pyplot as plt
This allows programmers to append the shorter word plt to any of the functions available within the module, as in plt.show(). You can see this alias import statement in use within our “How to Plot Data in Python 3 Using matplotlib tutorial.”

Conclusion
When we import modules we’re able to call functions that are not built into Python. Some modules are installed as part of Python, and some we will install through pip.

Making use of modules allows us to make our programs more robust and powerful as we’re leveraging existing code. We can also create our own modules for ourselves and for other programmers to use in future programs.

