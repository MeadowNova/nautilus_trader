from __future__ import annotations


def knuth_morris_pratt(text: str, pattern: str) -> int:
    """
    The Knuth-Morris-Pratt Algorithm for finding a pattern within a piece of text
    with complexity O(n + m)

    1) Preprocess pattern to identify any suffixes that are identical to prefixes

        This tells us where to continue from if we get a mismatch between a character
        in our pattern and the text.

    2) Step through the text one character at a time and compare it to a character in
        the pattern updating our location within the pattern if necessary

    >>> kmp = "knuth_morris_pratt"
    >>> all(
    ...    knuth_morris_pratt(kmp, s) == kmp.find(s)
    ...    for s in ("kn", "h_m", "rr", "tt", "not there")
    ... )
    True
    """

    # 1) Construct the failure array
    failure = get_failure_array(pattern)

    # 2) Step through text searching for pattern
    i, j = 0, 0  # index into text, pattern
    while i < len(text):
        if pattern[j] == text[i]:
            if j == (len(pattern) - 1):
                return i - j
            j += 1

        # if this is a prefix in our pattern
        # just go back far enough to continue
        elif j > 0:
            j = failure[j - 1]
            continue
        i += 1
    return -1


def get_failure_array(pattern: str) -> list[int]:
    """
    Calculates the new index we should go to if we fail a comparison
    :param pattern:
    :return:
    """
    failure = [0]
    i = 0
    j = 1
    while j < len(pattern):
        if pattern[i] == pattern[j]:
            i += 1
        elif i > 0:
            i = failure[i - 1]
            continue
        j += 1
        failure.append(i)
    return failure


if __name__ == "__main__":
    import doctest

    doctest.testmod()

    # Test 1)
    pattern = "abc1abc12"
    text1 = "alskfjaldsabc1abc1abc12k23adsfabcabc"
    text2 = "alskfjaldsk23adsfabcabc"
    assert knuth_morris_pratt(text1, pattern)
    assert knuth_morris_pratt(text2, pattern)

    # Test 2)
    pattern = "ABABX"
    text = "ABABZABABYABABX"
    assert knuth_morris_pratt(text, pattern)

    # Test 3)
    pattern = "AAAB"
    text = "ABAAAAAB"
    assert knuth_morris_pratt(text, pattern)

    # Test 4)
    pattern = "abcdabcy"
    text = "abcxabcdabxabcdabcdabcy"
    assert knuth_morris_pratt(text, pattern)

    # Test 5) -> Doctests
    kmp = "knuth_morris_pratt"
    assert all(
        knuth_morris_pratt(kmp, s) == kmp.find(s)
        for s in ("kn", "h_m", "rr", "tt", "not there")
    )

    # Test 6)
    pattern = "aabaabaaa"
    assert get_failure_array(pattern) == [0, 1, 0, 1, 2, 3, 4, 5, 2]


===============

# Numbers of alphabet which we call base
alphabet_size = 256
# Modulus to hash a string
modulus = 1000003


def rabin_karp(pattern: str, text: str) -> bool:
    """
    The Rabin-Karp Algorithm for finding a pattern within a piece of text
    with complexity O(nm), most efficient when it is used with multiple patterns
    as it is able to check if any of a set of patterns match a section of text in o(1)
    given the precomputed hashes.

    This will be the simple version which only assumes one pattern is being searched
    for but it's not hard to modify

    1) Calculate pattern hash

    2) Step through the text one character at a time passing a window with the same
        length as the pattern
        calculating the hash of the text within the window compare it with the hash
        of the pattern. Only testing equality if the hashes match
    """
    p_len = len(pattern)
    t_len = len(text)
    if p_len > t_len:
        return False

    p_hash = 0
    text_hash = 0
    modulus_power = 1

    # Calculating the hash of pattern and substring of text
    for i in range(p_len):
        p_hash = (ord(pattern[i]) + p_hash * alphabet_size) % modulus
        text_hash = (ord(text[i]) + text_hash * alphabet_size) % modulus
        if i == p_len - 1:
            continue
        modulus_power = (modulus_power * alphabet_size) % modulus

    for i in range(t_len - p_len + 1):
        if text_hash == p_hash and text[i : i + p_len] == pattern:
            return True
        if i == t_len - p_len:
            continue
        # Calculate the https://en.wikipedia.org/wiki/Rolling_hash
        text_hash = (
            (text_hash - ord(text[i]) * modulus_power) * alphabet_size
            + ord(text[i + p_len])
        ) % modulus
    return False


def test_rabin_karp() -> None:
    """
    >>> test_rabin_karp()
    Success.
    """
    # Test 1)
    pattern = "abc1abc12"
    text1 = "alskfjaldsabc1abc1abc12k23adsfabcabc"
    text2 = "alskfjaldsk23adsfabcabc"
    assert rabin_karp(pattern, text1)
    assert not rabin_karp(pattern, text2)

    # Test 2)
    pattern = "ABABX"
    text = "ABABZABABYABABX"
    assert rabin_karp(pattern, text)

    # Test 3)
    pattern = "AAAB"
    text = "ABAAAAAB"
    assert rabin_karp(pattern, text)

    # Test 4)
    pattern = "abcdabcy"
    text = "abcxabcdabxabcdabcdabcy"
    assert rabin_karp(pattern, text)

    # Test 5)
    pattern = "Lü"
    text = "Lüsai"
    assert rabin_karp(pattern, text)
    pattern = "Lue"
    assert not rabin_karp(pattern, text)
    print("Success.")


if __name__ == "__main__":
    test_rabin_karp()


=======================================

from __future__ import annotations

from collections import deque


class Automaton:
    def __init__(self, keywords: list[str]):
        self.adlist: list[dict] = []
        self.adlist.append(
            {"value": "", "next_states": [], "fail_state": 0, "output": []}
        )

        for keyword in keywords:
            self.add_keyword(keyword)
        self.set_fail_transitions()

    def find_next_state(self, current_state: int, char: str) -> int | None:
        for state in self.adlist[current_state]["next_states"]:
            if char == self.adlist[state]["value"]:
                return state
        return None

    def add_keyword(self, keyword: str) -> None:
        current_state = 0
        for character in keyword:
            next_state = self.find_next_state(current_state, character)
            if next_state is None:
                self.adlist.append(
                    {
                        "value": character,
                        "next_states": [],
                        "fail_state": 0,
                        "output": [],
                    }
                )
                self.adlist[current_state]["next_states"].append(len(self.adlist) - 1)
                current_state = len(self.adlist) - 1
            else:
                current_state = next_state
        self.adlist[current_state]["output"].append(keyword)

    def set_fail_transitions(self) -> None:
        q: deque = deque()
        for node in self.adlist[0]["next_states"]:
            q.append(node)
            self.adlist[node]["fail_state"] = 0
        while q:
            r = q.popleft()
            for child in self.adlist[r]["next_states"]:
                q.append(child)
                state = self.adlist[r]["fail_state"]
                while (
                    self.find_next_state(state, self.adlist[child]["value"]) is None
                    and state != 0
                ):
                    state = self.adlist[state]["fail_state"]
                self.adlist[child]["fail_state"] = self.find_next_state(
                    state, self.adlist[child]["value"]
                )
                if self.adlist[child]["fail_state"] is None:
                    self.adlist[child]["fail_state"] = 0
                self.adlist[child]["output"] = (
                    self.adlist[child]["output"]
                    + self.adlist[self.adlist[child]["fail_state"]]["output"]
                )

    def search_in(self, string: str) -> dict[str, list[int]]:
        """
        >>> A = Automaton(["what", "hat", "ver", "er"])
        >>> A.search_in("whatever, err ... , wherever")
        {'what': [0], 'hat': [1], 'ver': [5, 25], 'er': [6, 10, 22, 26]}
        """
        result: dict = {}  # returns a dict with keywords and list of its occurrences
        current_state = 0
        for i in range(len(string)):
            while (
                self.find_next_state(current_state, string[i]) is None
                and current_state != 0
            ):
                current_state = self.adlist[current_state]["fail_state"]
            next_state = self.find_next_state(current_state, string[i])
            if next_state is None:
                current_state = 0
            else:
                current_state = next_state
                for key in self.adlist[current_state]["output"]:
                    if key not in result:
                        result[key] = []
                    result[key].append(i - len(key) + 1)
        return result


if __name__ == "__main__":
    import doctest

    doctest.testmod()


================================
