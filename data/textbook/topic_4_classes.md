Python is an object-oriented programming language. Object-oriented programming (OOP) focuses on creating reusable patterns of code, in contrast to procedural programming, which focuses on explicit sequenced instructions. When working on complex programs in particular, object-oriented programming lets you reuse code and write code that is more readable, which in turn makes it more maintainable.

One of the most important concepts in object-oriented programming is the distinction between classes and objects, which are defined as follows:

Class — A blueprint created by a programmer for an object. This defines a set of attributes that will characterize any object that is instantiated from this class.
Object — An instance of a class. This is the realized version of the class, where the class is manifested in the program.
These are used to create patterns (in the case of classes) and then make use of the patterns (in the case of objects).

In this tutorial, we’ll go through creating classes, instantiating objects, initializing attributes with the constructor method, and working with more than one object of the same class.

Prerequisites
You should have Python 3 installed and a programming environment set up on your computer or server. If you don’t have a programming environment set up, you can refer to the installation and setup guides for a local programming environment or for a programming environment on your server appropriate for your operating system (Ubuntu, CentOS, Debian, etc.)

Classes
Classes are like a blueprint or a prototype that you can define to use to create objects.

We define classes by using the class keyword, similar to how we define functions by using the def keyword.

Info: To follow along with the example code in this tutorial, open a Python interactive shell on your local system by running the python3 command. Then you can copy, paste, or edit the examples by adding them after the >>> prompt.

Let’s define a class called Shark that has two functions associated with it, one for swimming and one for being awesome:

shark.py
class Shark:
    def swim(self):
        print("The shark is swimming.")

    def be_awesome(self):
        print("The shark is being awesome.")
Because these functions are indented under the class Shark, they are called methods. Methods are a special kind of function that are defined within a class.

The argument to these functions is the word self, which is a reference to objects that are made based on this class. To reference instances (or objects) of the class, self will always be the first parameter, but it need not be the only one.

Defining this class did not create any Shark objects, only the pattern for a Shark object that we can define later. That is, if you run the program above at this stage nothing will be returned.

Creating the Shark class above provided us with a blueprint for an object.

Objects
An object is an instance of a class. We can take the Shark class defined above, and use it to create an object or instance of it.

We’ll make a Shark object called sammy:

sammy = Shark()
Here, we initialized the object sammy as an instance of the class by setting it equal to Shark().

Now, let’s use the two methods with the Shark object sammy:

sammy = Shark()
sammy.swim()
sammy.be_awesome()
The Shark object sammy is using the two methods swim() and be_awesome(). We called these using the dot operator (.), which is used to reference an attribute of the object. In this case, the attribute is a method and it’s called with parentheses, like how you would also call with a function.

Because the keyword self was a parameter of the methods as defined in the Shark class, the sammy object gets passed to the methods. The self parameter ensures that the methods have a way of referring to object attributes.

When we call the methods, however, nothing is passed inside the parentheses, the object sammy is being automatically passed with the dot operator.

Let’s add the object within the context of a program:

shark.py
class Shark:
    def swim(self):
        print("The shark is swimming.")

    def be_awesome(self):
        print("The shark is being awesome.")


def main():
    sammy = Shark()
    sammy.swim()
    sammy.be_awesome()

if __name__ == "__main__":
    main()

Let’s run the program to see what it does:

python shark.py
Output
The shark is swimming.
The shark is being awesome.
The object sammy calls the two methods in the main() function of the program, causing those methods to run.

The Constructor Method
The constructor method is used to initialize data. It is run as soon as an object of a class is instantiated. Also known as the __init__ method, it will be the first definition of a class and looks like this:

class Shark:
    def __init__(self):
        print("This is the constructor method.")
If you added the above __init__ method to the Shark class in the program above, the program would output the following without your modifying anything within the sammy instantiation:

Output
This is the constructor method.
The shark is swimming.
The shark is being awesome.
This is because the constructor method is automatically initialized. You should use this method to carry out any initializing you would like to do with your class objects.

Instead of using the constructor method above, let’s create one that uses a name variable that we can use to assign names to objects. We’ll pass name as a parameter and set self.name equal to name:

shark.py
class Shark:
    def __init__(self, name):
        self.name = name
Next, we can modify the strings in our functions to reference the names, as the following:

shark.py
class Shark:
    def __init__(self, name):
        self.name = name

    def swim(self):
        # Reference the name
        print(self.name + " is swimming.")

    def be_awesome(self):
        # Reference the name
        print(self.name + " is being awesome.")
Finally, we can set the name of the Shark object sammy as equal to "Sammy" by passing it as a parameter of the Shark class:

shark.py
class Shark:
    def __init__(self, name):
        self.name = name

    def swim(self):
        print(self.name + " is swimming.")

    def be_awesome(self):
        print(self.name + " is being awesome.")


def main():
    # Set name of Shark object
    sammy = Shark("Sammy")
    sammy.swim()
    sammy.be_awesome()

if __name__ == "__main__":
    main()

We can run the program now:

python shark.py
Output
Sammy is swimming.
Sammy is being awesome.
We see that the name we passed to the object is being printed out. We defined the __init__ method with the parameter name (along with the self keyword) and defined a variable within the method.

Because the constructor method is automatically initialized, we do not need to explicitly call it, only pass the arguments in the parentheses following the class name when we create a new instance of the class.

If we wanted to add another parameter, such as age, we could do so by also passing it to the __init__ method:

class Shark:
    def __init__(self, name, age):
        self.name = name
        self.age = age
Then, when we create our object sammy, we can pass Sammy’s age in our statement:

sammy = Shark("Sammy", 5)
To make use of age, we would need to also create a method in the class that calls for it.

Constructor methods allow us to initialize certain attributes of an object.

Working with More Than One Object
Classes are useful because they allow us to create many similar objects based on the same blueprint.

To get a sense for how this works, let’s add another Shark object to our program:

shark.py
class Shark:
    def __init__(self, name):
        self.name = name

    def swim(self):
        print(self.name + " is swimming.")

    def be_awesome(self):
        print(self.name + " is being awesome.")

def main():
    sammy = Shark("Sammy")
    sammy.be_awesome()
    stevie = Shark("Stevie")
    stevie.swim()

if __name__ == "__main__":
  main()

We have created a second Shark object called stevie and passed the name "Stevie" to it. In this example, we used the be_awesome() method with sammy and the swim() method with stevie.

Let’s run the program:

python shark.py
Output
Sammy is being awesome.
Stevie is swimming.
The output shows that we are using two different objects, the sammy object and the stevie object, both of the Shark class.

Classes make it possible to create more than one object following the same pattern without creating each one from scratch.