#!/usr/bin/env python3

"""
Pure Python implementations of binary search algorithms

For doctests run the following command:
python3 -m doctest -v binary_search.py

For manual testing run:
python3 binary_search.py
"""

from __future__ import annotations

import bisect


def bisect_left(
    sorted_collection: list[int], item: int, lo: int = 0, hi: int = -1
) -> int:
    """
    Locates the first element in a sorted array that is larger or equal to a given
    value.

    It has the same interface as
    https://docs.python.org/3/library/bisect.html#bisect.bisect_left .

    :param sorted_collection: some ascending sorted collection with comparable items
    :param item: item to bisect
    :param lo: lowest index to consider (as in sorted_collection[lo:hi])
    :param hi: past the highest index to consider (as in sorted_collection[lo:hi])
    :return: index i such that all values in sorted_collection[lo:i] are < item and all
        values in sorted_collection[i:hi] are >= item.

    Examples:
    >>> bisect_left([0, 5, 7, 10, 15], 0)
    0
    >>> bisect_left([0, 5, 7, 10, 15], 6)
    2
    >>> bisect_left([0, 5, 7, 10, 15], 20)
    5
    >>> bisect_left([0, 5, 7, 10, 15], 15, 1, 3)
    3
    >>> bisect_left([0, 5, 7, 10, 15], 6, 2)
    2
    """
    if hi < 0:
        hi = len(sorted_collection)

    while lo < hi:
        mid = lo + (hi - lo) // 2
        if sorted_collection[mid] < item:
            lo = mid + 1
        else:
            hi = mid

    return lo


def bisect_right(
    sorted_collection: list[int], item: int, lo: int = 0, hi: int = -1
) -> int:
    """
    Locates the first element in a sorted array that is larger than a given value.

    It has the same interface as
    https://docs.python.org/3/library/bisect.html#bisect.bisect_right .

    :param sorted_collection: some ascending sorted collection with comparable items
    :param item: item to bisect
    :param lo: lowest index to consider (as in sorted_collection[lo:hi])
    :param hi: past the highest index to consider (as in sorted_collection[lo:hi])
    :return: index i such that all values in sorted_collection[lo:i] are <= item and
        all values in sorted_collection[i:hi] are > item.

    Examples:
    >>> bisect_right([0, 5, 7, 10, 15], 0)
    1
    >>> bisect_right([0, 5, 7, 10, 15], 15)
    5
    >>> bisect_right([0, 5, 7, 10, 15], 6)
    2
    >>> bisect_right([0, 5, 7, 10, 15], 15, 1, 3)
    3
    >>> bisect_right([0, 5, 7, 10, 15], 6, 2)
    2
    """
    if hi < 0:
        hi = len(sorted_collection)

    while lo < hi:
        mid = lo + (hi - lo) // 2
        if sorted_collection[mid] <= item:
            lo = mid + 1
        else:
            hi = mid

    return lo


def insort_left(
    sorted_collection: list[int], item: int, lo: int = 0, hi: int = -1
) -> None:
    """
    Inserts a given value into a sorted array before other values with the same value.

    It has the same interface as
    https://docs.python.org/3/library/bisect.html#bisect.insort_left .

    :param sorted_collection: some ascending sorted collection with comparable items
    :param item: item to insert
    :param lo: lowest index to consider (as in sorted_collection[lo:hi])
    :param hi: past the highest index to consider (as in sorted_collection[lo:hi])

    Examples:
    >>> sorted_collection = [0, 5, 7, 10, 15]
    >>> insort_left(sorted_collection, 6)
    >>> sorted_collection
    [0, 5, 6, 7, 10, 15]
    >>> sorted_collection = [(0, 0), (5, 5), (7, 7), (10, 10), (15, 15)]
    >>> item = (5, 5)
    >>> insort_left(sorted_collection, item)
    >>> sorted_collection
    [(0, 0), (5, 5), (5, 5), (7, 7), (10, 10), (15, 15)]
    >>> item is sorted_collection[1]
    True
    >>> item is sorted_collection[2]
    False
    >>> sorted_collection = [0, 5, 7, 10, 15]
    >>> insort_left(sorted_collection, 20)
    >>> sorted_collection
    [0, 5, 7, 10, 15, 20]
    >>> sorted_collection = [0, 5, 7, 10, 15]
    >>> insort_left(sorted_collection, 15, 1, 3)
    >>> sorted_collection
    [0, 5, 7, 15, 10, 15]
    """
    sorted_collection.insert(bisect_left(sorted_collection, item, lo, hi), item)


def insort_right(
    sorted_collection: list[int], item: int, lo: int = 0, hi: int = -1
) -> None:
    """
    Inserts a given value into a sorted array after other values with the same value.

    It has the same interface as
    https://docs.python.org/3/library/bisect.html#bisect.insort_right .

    :param sorted_collection: some ascending sorted collection with comparable items
    :param item: item to insert
    :param lo: lowest index to consider (as in sorted_collection[lo:hi])
    :param hi: past the highest index to consider (as in sorted_collection[lo:hi])

    Examples:
    >>> sorted_collection = [0, 5, 7, 10, 15]
    >>> insort_right(sorted_collection, 6)
    >>> sorted_collection
    [0, 5, 6, 7, 10, 15]
    >>> sorted_collection = [(0, 0), (5, 5), (7, 7), (10, 10), (15, 15)]
    >>> item = (5, 5)
    >>> insort_right(sorted_collection, item)
    >>> sorted_collection
    [(0, 0), (5, 5), (5, 5), (7, 7), (10, 10), (15, 15)]
    >>> item is sorted_collection[1]
    False
    >>> item is sorted_collection[2]
    True
    >>> sorted_collection = [0, 5, 7, 10, 15]
    >>> insort_right(sorted_collection, 20)
    >>> sorted_collection
    [0, 5, 7, 10, 15, 20]
    >>> sorted_collection = [0, 5, 7, 10, 15]
    >>> insort_right(sorted_collection, 15, 1, 3)
    >>> sorted_collection
    [0, 5, 7, 15, 10, 15]
    """
    sorted_collection.insert(bisect_right(sorted_collection, item, lo, hi), item)


def binary_search(sorted_collection: list[int], item: int) -> int:
    """Pure implementation of a binary search algorithm in Python

    Be careful collection must be ascending sorted otherwise, the result will be
    unpredictable

    :param sorted_collection: some ascending sorted collection with comparable items
    :param item: item value to search
    :return: index of the found item or -1 if the item is not found

    Examples:
    >>> binary_search([0, 5, 7, 10, 15], 0)
    0
    >>> binary_search([0, 5, 7, 10, 15], 15)
    4
    >>> binary_search([0, 5, 7, 10, 15], 5)
    1
    >>> binary_search([0, 5, 7, 10, 15], 6)
    -1
    """
    if list(sorted_collection) != sorted(sorted_collection):
        raise ValueError("sorted_collection must be sorted in ascending order")
    left = 0
    right = len(sorted_collection) - 1

    while left <= right:
        midpoint = left + (right - left) // 2
        current_item = sorted_collection[midpoint]
        if current_item == item:
            return midpoint
        elif item < current_item:
            right = midpoint - 1
        else:
            left = midpoint + 1
    return -1


def binary_search_std_lib(sorted_collection: list[int], item: int) -> int:
    """Pure implementation of a binary search algorithm in Python using stdlib

    Be careful collection must be ascending sorted otherwise, the result will be
    unpredictable

    :param sorted_collection: some ascending sorted collection with comparable items
    :param item: item value to search
    :return: index of the found item or -1 if the item is not found

    Examples:
    >>> binary_search_std_lib([0, 5, 7, 10, 15], 0)
    0
    >>> binary_search_std_lib([0, 5, 7, 10, 15], 15)
    4
    >>> binary_search_std_lib([0, 5, 7, 10, 15], 5)
    1
    >>> binary_search_std_lib([0, 5, 7, 10, 15], 6)
    -1
    """
    if list(sorted_collection) != sorted(sorted_collection):
        raise ValueError("sorted_collection must be sorted in ascending order")
    index = bisect.bisect_left(sorted_collection, item)
    if index != len(sorted_collection) and sorted_collection[index] == item:
        return index
    return -1


def binary_search_by_recursion(
    sorted_collection: list[int], item: int, left: int = 0, right: int = -1
) -> int:
    """Pure implementation of a binary search algorithm in Python by recursion

    Be careful collection must be ascending sorted otherwise, the result will be
    unpredictable
    First recursion should be started with left=0 and right=(len(sorted_collection)-1)

    :param sorted_collection: some ascending sorted collection with comparable items
    :param item: item value to search
    :return: index of the found item or -1 if the item is not found

    Examples:
    >>> binary_search_by_recursion([0, 5, 7, 10, 15], 0, 0, 4)
    0
    >>> binary_search_by_recursion([0, 5, 7, 10, 15], 15, 0, 4)
    4
    >>> binary_search_by_recursion([0, 5, 7, 10, 15], 5, 0, 4)
    1
    >>> binary_search_by_recursion([0, 5, 7, 10, 15], 6, 0, 4)
    -1
    """
    if right < 0:
        right = len(sorted_collection) - 1
    if list(sorted_collection) != sorted(sorted_collection):
        raise ValueError("sorted_collection must be sorted in ascending order")
    if right < left:
        return -1

    midpoint = left + (right - left) // 2

    if sorted_collection[midpoint] == item:
        return midpoint
    elif sorted_collection[midpoint] > item:
        return binary_search_by_recursion(sorted_collection, item, left, midpoint - 1)
    else:
        return binary_search_by_recursion(sorted_collection, item, midpoint + 1, right)


def exponential_search(sorted_collection: list[int], item: int) -> int:
    """Pure implementation of an exponential search algorithm in Python
    Resources used:
    https://en.wikipedia.org/wiki/Exponential_search

    Be careful collection must be ascending sorted otherwise, result will be
    unpredictable

    :param sorted_collection: some ascending sorted collection with comparable items
    :param item: item value to search
    :return: index of the found item or -1 if the item is not found

    the order of this algorithm is O(lg I) where I is index position of item if exist

    Examples:
    >>> exponential_search([0, 5, 7, 10, 15], 0)
    0
    >>> exponential_search([0, 5, 7, 10, 15], 15)
    4
    >>> exponential_search([0, 5, 7, 10, 15], 5)
    1
    >>> exponential_search([0, 5, 7, 10, 15], 6)
    -1
    """
    if list(sorted_collection) != sorted(sorted_collection):
        raise ValueError("sorted_collection must be sorted in ascending order")
    bound = 1
    while bound < len(sorted_collection) and sorted_collection[bound] < item:
        bound *= 2
    left = bound // 2
    right = min(bound, len(sorted_collection) - 1)
    last_result = binary_search_by_recursion(
        sorted_collection=sorted_collection, item=item, left=left, right=right
    )
    if last_result is None:
        return -1
    return last_result


searches = (  # Fastest to slowest...
    binary_search_std_lib,
    binary_search,
    exponential_search,
    binary_search_by_recursion,
)


if __name__ == "__main__":
    import doctest
    import timeit

    doctest.testmod()
    for search in searches:
        name = f"{search.__name__:>26}"
        print(f"{name}: {search([0, 5, 7, 10, 15], 10) = }")  # type: ignore[operator]

    print("\nBenchmarks...")
    setup = "collection = range(1000)"
    for search in searches:
        name = search.__name__
        print(
            f"{name:>26}:",
            timeit.timeit(
                f"{name}(collection, 500)", setup=setup, number=5_000, globals=globals()
            ),
        )

    user_input = input("\nEnter numbers separated by comma: ").strip()
    collection = sorted(int(item) for item in user_input.split(","))
    target = int(input("Enter a single number to be found in the list: "))
    result = binary_search(sorted_collection=collection, item=target)
    if result == -1:
        print(f"{target} was not found in {collection}.")
    else:
        print(f"{target} was found at position {result} of {collection}.")

======================

#!/usr/bin/env python3

"""
Pure Python implementation of exponential search algorithm

For more information, see the Wikipedia page:
https://en.wikipedia.org/wiki/Exponential_search

For doctests run the following command:
python3 -m doctest -v exponential_search.py

For manual testing run:
python3 exponential_search.py
"""

from __future__ import annotations


def binary_search_by_recursion(
    sorted_collection: list[int], item: int, left: int = 0, right: int = -1
) -> int:
    """Pure implementation of binary search algorithm in Python using recursion

    Be careful: the collection must be ascending sorted otherwise, the result will be
    unpredictable.

    :param sorted_collection: some ascending sorted collection with comparable items
    :param item: item value to search
    :param left: starting index for the search
    :param right: ending index for the search
    :return: index of the found item or -1 if the item is not found

    Examples:
    >>> binary_search_by_recursion([0, 5, 7, 10, 15], 0, 0, 4)
    0
    >>> binary_search_by_recursion([0, 5, 7, 10, 15], 15, 0, 4)
    4
    >>> binary_search_by_recursion([0, 5, 7, 10, 15], 5, 0, 4)
    1
    >>> binary_search_by_recursion([0, 5, 7, 10, 15], 6, 0, 4)
    -1
    """
    if right < 0:
        right = len(sorted_collection) - 1
    if list(sorted_collection) != sorted(sorted_collection):
        raise ValueError("sorted_collection must be sorted in ascending order")
    if right < left:
        return -1

    midpoint = left + (right - left) // 2

    if sorted_collection[midpoint] == item:
        return midpoint
    elif sorted_collection[midpoint] > item:
        return binary_search_by_recursion(sorted_collection, item, left, midpoint - 1)
    else:
        return binary_search_by_recursion(sorted_collection, item, midpoint + 1, right)


def exponential_search(sorted_collection: list[int], item: int) -> int:
    """
    Pure implementation of an exponential search algorithm in Python.
    For more information, refer to:
    https://en.wikipedia.org/wiki/Exponential_search

    Be careful: the collection must be ascending sorted, otherwise the result will be
    unpredictable.

    :param sorted_collection: some ascending sorted collection with comparable items
    :param item: item value to search
    :return: index of the found item or -1 if the item is not found

    The time complexity of this algorithm is O(log i) where i is the index of the item.

    Examples:
    >>> exponential_search([0, 5, 7, 10, 15], 0)
    0
    >>> exponential_search([0, 5, 7, 10, 15], 15)
    4
    >>> exponential_search([0, 5, 7, 10, 15], 5)
    1
    >>> exponential_search([0, 5, 7, 10, 15], 6)
    -1
    """
    if list(sorted_collection) != sorted(sorted_collection):
        raise ValueError("sorted_collection must be sorted in ascending order")

    if sorted_collection[0] == item:
        return 0

    bound = 1
    while bound < len(sorted_collection) and sorted_collection[bound] < item:
        bound *= 2

    left = bound // 2
    right = min(bound, len(sorted_collection) - 1)
    return binary_search_by_recursion(sorted_collection, item, left, right)


if __name__ == "__main__":
    import doctest

    doctest.testmod()

    # Manual testing
    user_input = input("Enter numbers separated by commas: ").strip()
    collection = sorted(int(item) for item in user_input.split(","))
    target = int(input("Enter a number to search for: "))
    result = exponential_search(sorted_collection=collection, item=target)
    if result == -1:
        print(f"{target} was not found in {collection}.")
    else:
        print(f"{target} was found at index {result} in {collection}.")

==================================

"""
This is pure Python implementation of fibonacci search.

Resources used:
https://en.wikipedia.org/wiki/Fibonacci_search_technique

For doctests run following command:
python3 -m doctest -v fibonacci_search.py

For manual testing run:
python3 fibonacci_search.py
"""

from functools import lru_cache


@lru_cache
def fibonacci(k: int) -> int:
    """Finds fibonacci number in index k.

    Parameters
    ----------
    k :
        Index of fibonacci.

    Returns
    -------
    int
        Fibonacci number in position k.

    >>> fibonacci(0)
    0
    >>> fibonacci(2)
    1
    >>> fibonacci(5)
    5
    >>> fibonacci(15)
    610
    >>> fibonacci('a')
    Traceback (most recent call last):
    TypeError: k must be an integer.
    >>> fibonacci(-5)
    Traceback (most recent call last):
    ValueError: k integer must be greater or equal to zero.
    """
    if not isinstance(k, int):
        raise TypeError("k must be an integer.")
    if k < 0:
        raise ValueError("k integer must be greater or equal to zero.")
    if k == 0:
        return 0
    elif k == 1:
        return 1
    else:
        return fibonacci(k - 1) + fibonacci(k - 2)


def fibonacci_search(arr: list, val: int) -> int:
    """A pure Python implementation of a fibonacci search algorithm.

    Parameters
    ----------
    arr
        List of sorted elements.
    val
        Element to search in list.

    Returns
    -------
    int
        The index of the element in the array.
        -1 if the element is not found.

    >>> fibonacci_search([4, 5, 6, 7], 4)
    0
    >>> fibonacci_search([4, 5, 6, 7], -10)
    -1
    >>> fibonacci_search([-18, 2], -18)
    0
    >>> fibonacci_search([5], 5)
    0
    >>> fibonacci_search(['a', 'c', 'd'], 'c')
    1
    >>> fibonacci_search(['a', 'c', 'd'], 'f')
    -1
    >>> fibonacci_search([], 1)
    -1
    >>> fibonacci_search([.1, .4 , 7], .4)
    1
    >>> fibonacci_search([], 9)
    -1
    >>> fibonacci_search(list(range(100)), 63)
    63
    >>> fibonacci_search(list(range(100)), 99)
    99
    >>> fibonacci_search(list(range(-100, 100, 3)), -97)
    1
    >>> fibonacci_search(list(range(-100, 100, 3)), 0)
    -1
    >>> fibonacci_search(list(range(-100, 100, 5)), 0)
    20
    >>> fibonacci_search(list(range(-100, 100, 5)), 95)
    39
    """
    len_list = len(arr)
    # Find m such that F_m >= n where F_i is the i_th fibonacci number.
    i = 0
    while True:
        if fibonacci(i) >= len_list:
            fibb_k = i
            break
        i += 1
    offset = 0
    while fibb_k > 0:
        index_k = min(
            offset + fibonacci(fibb_k - 1), len_list - 1
        )  # Prevent out of range
        item_k_1 = arr[index_k]
        if item_k_1 == val:
            return index_k
        elif val < item_k_1:
            fibb_k -= 1
        elif val > item_k_1:
            offset += fibonacci(fibb_k - 1)
            fibb_k -= 2
    return -1


if __name__ == "__main__":
    import doctest

    doctest.testmod()

========================================

# https://en.wikipedia.org/wiki/Simulated_annealing
import math
import random
from typing import Any

from .hill_climbing import SearchProblem


def simulated_annealing(
    search_prob,
    find_max: bool = True,
    max_x: float = math.inf,
    min_x: float = -math.inf,
    max_y: float = math.inf,
    min_y: float = -math.inf,
    visualization: bool = False,
    start_temperate: float = 100,
    rate_of_decrease: float = 0.01,
    threshold_temp: float = 1,
) -> Any:
    """
    Implementation of the simulated annealing algorithm. We start with a given state,
    find all its neighbors. Pick a random neighbor, if that neighbor improves the
    solution, we move in that direction, if that neighbor does not improve the solution,
    we generate a random real number between 0 and 1, if the number is within a certain
    range (calculated using temperature) we move in that direction, else we pick
    another neighbor randomly and repeat the process.

    Args:
        search_prob: The search state at the start.
        find_max: If True, the algorithm should find the minimum else the minimum.
        max_x, min_x, max_y, min_y: the maximum and minimum bounds of x and y.
        visualization: If True, a matplotlib graph is displayed.
        start_temperate: the initial temperate of the system when the program starts.
        rate_of_decrease: the rate at which the temperate decreases in each iteration.
        threshold_temp: the threshold temperature below which we end the search
    Returns a search state having the maximum (or minimum) score.
    """
    search_end = False
    current_state = search_prob
    current_temp = start_temperate
    scores = []
    iterations = 0
    best_state = None

    while not search_end:
        current_score = current_state.score()
        if best_state is None or current_score > best_state.score():
            best_state = current_state
        scores.append(current_score)
        iterations += 1
        next_state = None
        neighbors = current_state.get_neighbors()
        while (
            next_state is None and neighbors
        ):  # till we do not find a neighbor that we can move to
            index = random.randint(0, len(neighbors) - 1)  # picking a random neighbor
            picked_neighbor = neighbors.pop(index)
            change = picked_neighbor.score() - current_score

            if (
                picked_neighbor.x > max_x
                or picked_neighbor.x < min_x
                or picked_neighbor.y > max_y
                or picked_neighbor.y < min_y
            ):
                continue  # neighbor outside our bounds

            if not find_max:
                change = change * -1  # in case we are finding minimum
            if change > 0:  # improves the solution
                next_state = picked_neighbor
            else:
                probability = (math.e) ** (
                    change / current_temp
                )  # probability generation function
                if random.random() < probability:  # random number within probability
                    next_state = picked_neighbor
        current_temp = current_temp - (current_temp * rate_of_decrease)

        if current_temp < threshold_temp or next_state is None:
            # temperature below threshold, or could not find a suitable neighbor
            search_end = True
        else:
            current_state = next_state

    if visualization:
        from matplotlib import pyplot as plt

        plt.plot(range(iterations), scores)
        plt.xlabel("Iterations")
        plt.ylabel("Function values")
        plt.show()
    return best_state


if __name__ == "__main__":

    def test_f1(x, y):
        return (x**2) + (y**2)

    # starting the problem with initial coordinates (12, 47)
    prob = SearchProblem(x=12, y=47, step_size=1, function_to_optimize=test_f1)
    local_min = simulated_annealing(
        prob, find_max=False, max_x=100, min_x=5, max_y=50, min_y=-5, visualization=True
    )
    print(
        "The minimum score for f(x, y) = x^2 + y^2 with the domain 100 > x > 5 "
        f"and 50 > y > - 5 found via hill climbing: {local_min.score()}"
    )

    # starting the problem with initial coordinates (12, 47)
    prob = SearchProblem(x=12, y=47, step_size=1, function_to_optimize=test_f1)
    local_min = simulated_annealing(
        prob, find_max=True, max_x=100, min_x=5, max_y=50, min_y=-5, visualization=True
    )
    print(
        "The maximum score for f(x, y) = x^2 + y^2 with the domain 100 > x > 5 "
        f"and 50 > y > - 5 found via hill climbing: {local_min.score()}"
    )

    def test_f2(x, y):
        return (3 * x**2) - (6 * y)

    prob = SearchProblem(x=3, y=4, step_size=1, function_to_optimize=test_f1)
    local_min = simulated_annealing(prob, find_max=False, visualization=True)
    print(
        "The minimum score for f(x, y) = 3*x^2 - 6*y found via hill climbing: "
        f"{local_min.score()}"
    )

    prob = SearchProblem(x=3, y=4, step_size=1, function_to_optimize=test_f1)
    local_min = simulated_annealing(prob, find_max=True, visualization=True)
    print(
        "The maximum score for f(x, y) = 3*x^2 - 6*y found via hill climbing: "
        f"{local_min.score()}"
    )

=================================================

from bisect import bisect
from itertools import accumulate


def frac_knapsack(vl, wt, w, n):
    """
    >>> frac_knapsack([60, 100, 120], [10, 20, 30], 50, 3)
    240.0
    >>> frac_knapsack([10, 40, 30, 50], [5, 4, 6, 3], 10, 4)
    105.0
    >>> frac_knapsack([10, 40, 30, 50], [5, 4, 6, 3], 8, 4)
    95.0
    >>> frac_knapsack([10, 40, 30, 50], [5, 4, 6], 8, 4)
    60.0
    >>> frac_knapsack([10, 40, 30], [5, 4, 6, 3], 8, 4)
    60.0
    >>> frac_knapsack([10, 40, 30, 50], [5, 4, 6, 3], 0, 4)
    0
    >>> frac_knapsack([10, 40, 30, 50], [5, 4, 6, 3], 8, 0)
    95.0
    >>> frac_knapsack([10, 40, 30, 50], [5, 4, 6, 3], -8, 4)
    0
    >>> frac_knapsack([10, 40, 30, 50], [5, 4, 6, 3], 8, -4)
    95.0
    >>> frac_knapsack([10, 40, 30, 50], [5, 4, 6, 3], 800, 4)
    130
    >>> frac_knapsack([10, 40, 30, 50], [5, 4, 6, 3], 8, 400)
    95.0
    >>> frac_knapsack("ABCD", [5, 4, 6, 3], 8, 400)
    Traceback (most recent call last):
        ...
    TypeError: unsupported operand type(s) for /: 'str' and 'int'
    """

    r = sorted(zip(vl, wt), key=lambda x: x[0] / x[1], reverse=True)
    vl, wt = [i[0] for i in r], [i[1] for i in r]
    acc = list(accumulate(wt))
    k = bisect(acc, w)
    return (
        0
        if k == 0
        else sum(vl[:k]) + (w - acc[k - 1]) * (vl[k]) / (wt[k])
        if k != n
        else sum(vl[:k])
    )


if __name__ == "__main__":
    import doctest

    doctest.testmod()

=================================

"""
Given a list of stock prices calculate the maximum profit that can be made from a
single buy and sell of one share of stock.  We only allowed to complete one buy
transaction and one sell transaction but must buy before we sell.

Example : prices = [7, 1, 5, 3, 6, 4]
max_profit will return 5 - which is by buying at price 1 and selling at price 6.

This problem can be solved using the concept of "GREEDY ALGORITHM".

We iterate over the price array once, keeping track of the lowest price point
(buy) and the maximum profit we can get at each point.  The greedy choice at each point
is to either buy at the current price if it's less than our current buying price, or
sell at the current price if the profit is more than our current maximum profit.
"""


def max_profit(prices: list[int]) -> int:
    """
    >>> max_profit([7, 1, 5, 3, 6, 4])
    5
    >>> max_profit([7, 6, 4, 3, 1])
    0
    """
    if not prices:
        return 0

    min_price = prices[0]
    max_profit: int = 0

    for price in prices:
        min_price = min(price, min_price)
        max_profit = max(price - min_price, max_profit)

    return max_profit


if __name__ == "__main__":
    import doctest

    doctest.testmod()
    print(max_profit([7, 1, 5, 3, 6, 4]))

==================================
