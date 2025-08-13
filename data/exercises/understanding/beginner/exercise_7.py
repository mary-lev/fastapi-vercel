def xor(b1, b2):
    if b1 or b2:
        return not b1 or not b2
    else:
        return False


print(xor(True, True))
