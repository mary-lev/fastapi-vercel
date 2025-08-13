# Test case for the function
def test_cpa(doc_sections, expected):
    result = cpa(doc_sections)
    if expected == result:
        return True
    else:
        return False


# Code of the function
def cpa(doc_sections):
    result = {}

    cited_docs = set()
    for section in doc_sections:
        cited_docs.update(section)
    cited_docs = sorted(list(cited_docs))

    for idx, x in enumerate(cited_docs[:-1]):
        for y in cited_docs[idx + 1 :]:
            n = None
            for x_loc in locations(x, doc_sections):
                for y_loc in locations(y, doc_sections):
                    v = abs(x_loc - y_loc)
                    if n is None or v < n:
                        n = v

            result[(x, y)] = 1 / (2**n)

    return result


def locations(cit, secs):
    result = []

    for idx, sec in enumerate(secs):
        if cit in sec:
            result.append(idx)

    return result


# Tests
print(
    test_cpa(
        [{"A", "B"}, {"C"}, {"A", "C", "D"}],
        {("A", "B"): 1, ("A", "C"): 1, ("A", "D"): 1, ("B", "C"): 0.5, ("B", "D"): 0.25, ("C", "D"): 1},
    )
)
print(test_cpa([{"C", "B"}, {"B"}, {"A", "B"}], {("A", "B"): 1, ("A", "C"): 0.25, ("B", "C"): 1}))
