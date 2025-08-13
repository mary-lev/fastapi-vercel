# Test case for the function
def test_bib_coupling(list_of_docs, expected):
    result = bib_coupling(list_of_docs)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def bib_coupling(list_of_docs):
    overall_cs = 0
    comparisons = 0

    for idx, d in enumerate(list_of_docs):
        for e in list_of_docs[idx + 1 :]:
            comparisons += 1
            overall_cs += len(d.intersection(e))

    return overall_cs / comparisons


# Tests
print(test_bib_coupling([{"C", "D", "E", "F", "G"}, {"C", "F", "H", "I"}], 2))
print(test_bib_coupling([{"A", "B", "C"}, {"B", "D"}, {"A", "C", "E"}], 1))
print(test_bib_coupling([{"A", "B"}, {"A", "B"}, {"A", "B"}, {"C", "D"}], 1))
