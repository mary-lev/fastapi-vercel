# Test case for the algorithm
def test_contains_word(first_word, second_word, bib_entry, expected):
    result = contains_word(first_word, second_word, bib_entry)
    if expected == result:
        return True
    else:
        return False


# Code of the algorithm
def contains_word(first_word, second_word, bib_entry):
    return


# Three different test runs
print(
    test_contains_word(
        "Shotton", "Open", "Shotton, D. (2013). Open Citations. Nature, 502: 295–297. doi:10.1038/502295a", 2
    )
)
print(
    test_contains_word(
        "Citations", "Science", "Shotton, D. (2013). Open Citations. Nature, 502: 295–297. doi:10.1038/502295a", 1
    )
)
print(
    test_contains_word(
        "References", "1983", "Shotton, D. (2013). Open Citations. Nature, 502: 295–297. doi:10.1038/502295a", 0
    )
)
