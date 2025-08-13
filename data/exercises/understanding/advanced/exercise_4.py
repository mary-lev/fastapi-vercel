def validate(name):
    if not name.startswith("S"):
        name = "name:" + name

    is_valid = True

    if len(name) > 10:
        suffix = len(name[10:])
        if suffix > 10:
            is_valid = False
        else:
            tokens = name.split(" ")
            t_1 = tokens[0]
            t_2 = tokens[1]
            if t_1[len(t_1) - 1] != t_2[len(t_2) - 1]:
                is_valid = False

    return is_valid


def remove(is_valid, name):
    result = ""

    for c in name:
        if is_valid:
            result = result + c
            is_valid = False
        else:
            is_valid = True

    return result


my_name = input("Please provide a name (given name plus family name, separated by a space): ").strip()
print("Result:", remove(validate(my_name), my_name))
