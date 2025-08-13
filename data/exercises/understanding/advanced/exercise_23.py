from collections import deque


def f(m_string):
    c = 0
    s = deque(m_string)
    while s:
        cur = int(s.pop())
        if cur % 2:
            c = c + 1

    m_len = len(m_string)
    m_col = list()
    while c < m_len - c:
        m_col.append(m_string[c])
        c = c + 1

    for i, d in enumerate(reversed(m_string)):
        if d not in m_col:
            if i < len(m_col):
                m_col.insert(i, d)
            else:
                m_col.append(d)

    return m_col


my_mat_string = input("Please provide your matriculation number: ").strip()
print("Result:", f(my_mat_string))
