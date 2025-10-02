"""
Minimax helps to achieve maximum score in a game by checking all possible moves
depth is current depth in game tree.

nodeIndex is index of current node in scores[].
if move is of maximizer return true else false
leaves of game tree is stored in scores[]
height is maximum height of Game tree
"""

from __future__ import annotations

import math


def minimax(
    depth: int, node_index: int, is_max: bool, scores: list[int], height: float
) -> int:
    """
    This function implements the minimax algorithm, which helps achieve the optimal
    score for a player in a two-player game by checking all possible moves.
    If the player is the maximizer, then the score is maximized.
    If the player is the minimizer, then the score is minimized.

    Parameters:
    - depth: Current depth in the game tree.
    - node_index: Index of the current node in the scores list.
    - is_max: A boolean indicating whether the current move
              is for the maximizer (True) or minimizer (False).
    - scores: A list containing the scores of the leaves of the game tree.
    - height: The maximum height of the game tree.

    Returns:
    - An integer representing the optimal score for the current player.

    >>> import math
    >>> scores = [90, 23, 6, 33, 21, 65, 123, 34423]
    >>> height = math.log(len(scores), 2)
    >>> minimax(0, 0, True, scores, height)
    65
    >>> minimax(-1, 0, True, scores, height)
    Traceback (most recent call last):
        ...
    ValueError: Depth cannot be less than 0
    >>> minimax(0, 0, True, [], 2)
    Traceback (most recent call last):
        ...
    ValueError: Scores cannot be empty
    >>> scores = [3, 5, 2, 9, 12, 5, 23, 23]
    >>> height = math.log(len(scores), 2)
    >>> minimax(0, 0, True, scores, height)
    12
    """

    if depth < 0:
        raise ValueError("Depth cannot be less than 0")
    if len(scores) == 0:
        raise ValueError("Scores cannot be empty")

    # Base case: If the current depth equals the height of the tree,
    # return the score of the current node.
    if depth == height:
        return scores[node_index]

    # If it's the maximizer's turn, choose the maximum score
    # between the two possible moves.
    if is_max:
        return max(
            minimax(depth + 1, node_index * 2, False, scores, height),
            minimax(depth + 1, node_index * 2 + 1, False, scores, height),
        )

    # If it's the minimizer's turn, choose the minimum score
    # between the two possible moves.
    return min(
        minimax(depth + 1, node_index * 2, True, scores, height),
        minimax(depth + 1, node_index * 2 + 1, True, scores, height),
    )


def main() -> None:
    # Sample scores and height calculation
    scores = [90, 23, 6, 33, 21, 65, 123, 34423]
    height = math.log(len(scores), 2)

    # Calculate and print the optimal value using the minimax algorithm
    print("Optimal value : ", end="")
    print(minimax(0, 0, True, scores, height))


if __name__ == "__main__":
    import doctest

    doctest.testmod()
    main()


==================================

"""
In the Combination Sum problem, we are given a list consisting of distinct integers.
We need to find all the combinations whose sum equals to target given.
We can use an element more than one.

Time complexity(Average Case): O(n!)

Constraints:
1 <= candidates.length <= 30
2 <= candidates[i] <= 40
All elements of candidates are distinct.
1 <= target <= 40
"""


def backtrack(
    candidates: list, path: list, answer: list, target: int, previous_index: int
) -> None:
    """
    A recursive function that searches for possible combinations. Backtracks in case
    of a bigger current combination value than the target value.

    Parameters
    ----------
    previous_index: Last index from the previous search
    target: The value we need to obtain by summing our integers in the path list.
    answer: A list of possible combinations
    path: Current combination
    candidates: A list of integers we can use.
    """
    if target == 0:
        answer.append(path.copy())
    else:
        for index in range(previous_index, len(candidates)):
            if target >= candidates[index]:
                path.append(candidates[index])
                backtrack(candidates, path, answer, target - candidates[index], index)
                path.pop(len(path) - 1)


def combination_sum(candidates: list, target: int) -> list:
    """
    >>> combination_sum([2, 3, 5], 8)
    [[2, 2, 2, 2], [2, 3, 3], [3, 5]]
    >>> combination_sum([2, 3, 6, 7], 7)
    [[2, 2, 3], [7]]
    >>> combination_sum([-8, 2.3, 0], 1)
    Traceback (most recent call last):
        ...
    ValueError: All elements in candidates must be non-negative
    >>> combination_sum([], 1)
    Traceback (most recent call last):
        ...
    ValueError: Candidates list should not be empty
    """
    if not candidates:
        raise ValueError("Candidates list should not be empty")

    if any(x < 0 for x in candidates):
        raise ValueError("All elements in candidates must be non-negative")

    path = []  # type: list[int]
    answer = []  # type: list[int]
    backtrack(candidates, path, answer, target, 0)
    return answer


def main() -> None:
    print(combination_sum([-8, 2.3, 0], 1))


if __name__ == "__main__":
    import doctest

    doctest.testmod()
    main()

