def f(m_string):
    t = 0
    cl = list()
    for c in m_string:
        cl.append(int(c))
        t = t + int(c)

    eo_value = t % 2 == 0
    cl = on(cl, eo_value)
    idx = t % len(m_string)
    return cl[idx], cl


def on(ln, flag):
    c_len = len(ln)
    if c_len > 1:
        if (flag and ln[0] > ln[c_len - 1]) or (not flag and ln[0] < ln[c_len - 1]):
            t = ln[0]
            ln[0] = ln[c_len - 1]
            ln[c_len - 1] = t
        m = c_len // 2
        return on(ln[0:m], flag) + on(ln[m:c_len], flag)
    else:
        return ln


my_mat_string = input("Please provide your matriculation number: ").strip()
print("Result:", f(my_mat_string))
