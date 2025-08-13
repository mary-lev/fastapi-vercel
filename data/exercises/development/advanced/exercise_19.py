# Test case for the function
def test_cli(text, expected):
    result = cli(text)
    if round(expected, 3) == round(result, 3):
        return True
    else:
        return False


# Code of the function
def cli(text):
    n_words = len(text.split(" "))

    n_chars = 0
    n_sentences = 0
    for c in text.lower():
        if c in "qwertyuiopasdfghjklzxcvbnm1234567890":
            n_chars = n_chars + 1
        if c in ".!?;:":
            n_sentences = n_sentences + 1

    l = (n_chars / n_words) * 100
    s = (n_sentences / n_words) * 100

    return 0.0588 * l - 0.296 * s - 15.8


# Tests
print(test_cli("Test.", 0.0588 * (4 / 1) * 100 - 0.296 * (1 / 1) * 100 - 15.8))
print(
    test_cli(
        "After a while, finding that nothing more happened, she decided on going into the garden at once; but, alas for poor Alice! when she got to the door, she found she had forgotten the little golden key, and when she went back to the table for it, she found she could not possibly reach it: she could see it quite plainly through the glass, and she tried her best to climb up one of the legs of the table, but it was too slippery; and when she had tired herself out with trying, the poor little thing sat down and cried.",
        0.0588 * (402 / 101) * 100 - 0.296 * (5 / 101) * 100 - 15.8,
    )
)
