import math


class Graph:
    def __init__(self, n=0):  # a graph with Node 0,1,...,N-1
        self.n = n
        self.w = [
            [math.inf for j in range(n)] for i in range(n)
        ]  # adjacency matrix for weight
        self.dp = [
            [math.inf for j in range(n)] for i in range(n)
        ]  # dp[i][j] stores minimum distance from i to j

    def add_edge(self, u, v, w):
        """
        Adds a directed edge from node u
        to node v with weight w.

        >>> g = Graph(3)
        >>> g.add_edge(0, 1, 5)
        >>> g.dp[0][1]
        5
        """
        self.dp[u][v] = w

    def floyd_warshall(self):
        """
        Computes the shortest paths between all pairs of
        nodes using the Floyd-Warshall algorithm.

        >>> g = Graph(3)
        >>> g.add_edge(0, 1, 1)
        >>> g.add_edge(1, 2, 2)
        >>> g.floyd_warshall()
        >>> g.show_min(0, 2)
        3
        >>> g.show_min(2, 0)
        inf
        """
        for k in range(self.n):
            for i in range(self.n):
                for j in range(self.n):
                    self.dp[i][j] = min(self.dp[i][j], self.dp[i][k] + self.dp[k][j])

    def show_min(self, u, v):
        """
        Returns the minimum distance from node u to node v.

        >>> g = Graph(3)
        >>> g.add_edge(0, 1, 3)
        >>> g.add_edge(1, 2, 4)
        >>> g.floyd_warshall()
        >>> g.show_min(0, 2)
        7
        >>> g.show_min(1, 0)
        inf
        """
        return self.dp[u][v]


if __name__ == "__main__":
    import doctest

    doctest.testmod()

    # Example usage
    graph = Graph(5)
    graph.add_edge(0, 2, 9)
    graph.add_edge(0, 4, 10)
    graph.add_edge(1, 3, 5)
    graph.add_edge(2, 3, 7)
    graph.add_edge(3, 0, 10)
    graph.add_edge(3, 1, 2)
    graph.add_edge(3, 2, 1)
    graph.add_edge(3, 4, 6)
    graph.add_edge(4, 1, 3)
    graph.add_edge(4, 2, 4)
    graph.add_edge(4, 3, 9)
    graph.floyd_warshall()
    print(
        graph.show_min(1, 4)
    )  # Should output the minimum distance from node 1 to node 4
    print(
        graph.show_min(0, 3)
    )  # Should output the minimum distance from node 0 to node 3

==============================================
"""
Given weights and values of n items, put these items in a knapsack of
capacity W to get the maximum total value in the knapsack.

Note that only the integer weights 0-1 knapsack problem is solvable
using dynamic programming.
"""


def mf_knapsack(i, wt, val, j):
    """
    This code involves the concept of memory functions. Here we solve the subproblems
    which are needed unlike the below example
    F is a 2D array with ``-1`` s filled up
    """
    global f  # a global dp table for knapsack
    if f[i][j] < 0:
        if j < wt[i - 1]:
            val = mf_knapsack(i - 1, wt, val, j)
        else:
            val = max(
                mf_knapsack(i - 1, wt, val, j),
                mf_knapsack(i - 1, wt, val, j - wt[i - 1]) + val[i - 1],
            )
        f[i][j] = val
    return f[i][j]


def knapsack(w, wt, val, n):
    dp = [[0] * (w + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        for w_ in range(1, w + 1):
            if wt[i - 1] <= w_:
                dp[i][w_] = max(val[i - 1] + dp[i - 1][w_ - wt[i - 1]], dp[i - 1][w_])
            else:
                dp[i][w_] = dp[i - 1][w_]

    return dp[n][w_], dp


def knapsack_with_example_solution(w: int, wt: list, val: list):
    """
    Solves the integer weights knapsack problem returns one of
    the several possible optimal subsets.

    Parameters
    ----------

    * `w`: int, the total maximum weight for the given knapsack problem.
    * `wt`: list, the vector of weights for all items where ``wt[i]`` is the weight
       of the ``i``-th item.
    * `val`: list, the vector of values for all items where ``val[i]`` is the value
      of the ``i``-th item

    Returns
    -------

    * `optimal_val`: float, the optimal value for the given knapsack problem
    * `example_optional_set`: set, the indices of one of the optimal subsets
      which gave rise to the optimal value.

    Examples
    --------

    >>> knapsack_with_example_solution(10, [1, 3, 5, 2], [10, 20, 100, 22])
    (142, {2, 3, 4})
    >>> knapsack_with_example_solution(6, [4, 3, 2, 3], [3, 2, 4, 4])
    (8, {3, 4})
    >>> knapsack_with_example_solution(6, [4, 3, 2, 3], [3, 2, 4])
    Traceback (most recent call last):
        ...
    ValueError: The number of weights must be the same as the number of values.
    But got 4 weights and 3 values
    """
    if not (isinstance(wt, (list, tuple)) and isinstance(val, (list, tuple))):
        raise ValueError(
            "Both the weights and values vectors must be either lists or tuples"
        )

    num_items = len(wt)
    if num_items != len(val):
        msg = (
            "The number of weights must be the same as the number of values.\n"
            f"But got {num_items} weights and {len(val)} values"
        )
        raise ValueError(msg)
    for i in range(num_items):
        if not isinstance(wt[i], int):
            msg = (
                "All weights must be integers but got weight of "
                f"type {type(wt[i])} at index {i}"
            )
            raise TypeError(msg)

    optimal_val, dp_table = knapsack(w, wt, val, num_items)
    example_optional_set: set = set()
    _construct_solution(dp_table, wt, num_items, w, example_optional_set)

    return optimal_val, example_optional_set


def _construct_solution(dp: list, wt: list, i: int, j: int, optimal_set: set):
    """
    Recursively reconstructs one of the optimal subsets given
    a filled DP table and the vector of weights

    Parameters
    ----------

    * `dp`: list of list, the table of a solved integer weight dynamic programming
      problem
    * `wt`: list or tuple, the vector of weights of the items
    * `i`: int, the index of the item under consideration
    * `j`: int, the current possible maximum weight
    * `optimal_set`: set, the optimal subset so far. This gets modified by the function.

    Returns
    -------

    ``None``
    """
    # for the current item i at a maximum weight j to be part of an optimal subset,
    # the optimal value at (i, j) must be greater than the optimal value at (i-1, j).
    # where i - 1 means considering only the previous items at the given maximum weight
    if i > 0 and j > 0:
        if dp[i - 1][j] == dp[i][j]:
            _construct_solution(dp, wt, i - 1, j, optimal_set)
        else:
            optimal_set.add(i)
            _construct_solution(dp, wt, i - 1, j - wt[i - 1], optimal_set)


if __name__ == "__main__":
    """
    Adding test case for knapsack
    """
    val = [3, 2, 4, 4]
    wt = [4, 3, 2, 3]
    n = 4
    w = 6
    f = [[0] * (w + 1)] + [[0] + [-1] * (w + 1) for _ in range(n + 1)]
    optimal_solution, _ = knapsack(w, wt, val, n)
    print(optimal_solution)
    print(mf_knapsack(n, wt, val, w))  # switched the n and w

    # testing the dynamic programming problem with example
    # the optimal subset for the above example are items 3 and 4
    optimal_solution, optimal_subset = knapsack_with_example_solution(w, wt, val)
    assert optimal_solution == 8
    assert optimal_subset == {3, 4}
    print("optimal_value = ", optimal_solution)
    print("An optimal subset corresponding to the optimal value", optimal_subset)


================================

"""
LCS Problem Statement: Given two sequences, find the length of longest subsequence
present in both of them.  A subsequence is a sequence that appears in the same relative
order, but not necessarily continuous.
Example:"abc", "abg" are subsequences of "abcdefgh".
"""


def longest_common_subsequence(x: str, y: str):
    """
    Finds the longest common subsequence between two strings. Also returns the
    The subsequence found

    Parameters
    ----------

    x: str, one of the strings
    y: str, the other string

    Returns
    -------
    L[m][n]: int, the length of the longest subsequence. Also equal to len(seq)
    Seq: str, the subsequence found

    >>> longest_common_subsequence("programming", "gaming")
    (6, 'gaming')
    >>> longest_common_subsequence("physics", "smartphone")
    (2, 'ph')
    >>> longest_common_subsequence("computer", "food")
    (1, 'o')
    >>> longest_common_subsequence("", "abc")  # One string is empty
    (0, '')
    >>> longest_common_subsequence("abc", "")  # Other string is empty
    (0, '')
    >>> longest_common_subsequence("", "")  # Both strings are empty
    (0, '')
    >>> longest_common_subsequence("abc", "def")  # No common subsequence
    (0, '')
    >>> longest_common_subsequence("abc", "abc")  # Identical strings
    (3, 'abc')
    >>> longest_common_subsequence("a", "a")  # Single character match
    (1, 'a')
    >>> longest_common_subsequence("a", "b")  # Single character no match
    (0, '')
    >>> longest_common_subsequence("abcdef", "ace")  # Interleaved subsequence
    (3, 'ace')
    >>> longest_common_subsequence("ABCD", "ACBD")  # No repeated characters
    (3, 'ABD')
    """
    # find the length of strings

    assert x is not None
    assert y is not None

    m = len(x)
    n = len(y)

    # declaring the array for storing the dp values
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            match = 1 if x[i - 1] == y[j - 1] else 0

            dp[i][j] = max(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1] + match)

    seq = ""
    i, j = m, n
    while i > 0 and j > 0:
        match = 1 if x[i - 1] == y[j - 1] else 0

        if dp[i][j] == dp[i - 1][j - 1] + match:
            if match == 1:
                seq = x[i - 1] + seq
            i -= 1
            j -= 1
        elif dp[i][j] == dp[i - 1][j]:
            i -= 1
        else:
            j -= 1

    return dp[m][n], seq


if __name__ == "__main__":
    a = "AGGTAB"
    b = "GXTXAYB"
    expected_ln = 4
    expected_subseq = "GTAB"

    ln, subseq = longest_common_subsequence(a, b)
    print("len =", ln, ", sub-sequence =", subseq)
    import doctest

    doctest.testmod()


==============================================

"""
| Find the minimum number of multiplications needed to multiply chain of matrices.
| Reference: https://www.geeksforgeeks.org/matrix-chain-multiplication-dp-8/

The algorithm has interesting real-world applications.

Example:
  1. Image transformations in Computer Graphics as images are composed of matrix.
  2. Solve complex polynomial equations in the field of algebra using least processing
     power.
  3. Calculate overall impact of macroeconomic decisions as economic equations involve a
     number of variables.
  4. Self-driving car navigation can be made more accurate as matrix multiplication can
     accurately determine position and orientation of obstacles in short time.

Python doctests can be run with the following command::

  python -m doctest -v matrix_chain_multiply.py

Given a sequence ``arr[]`` that represents chain of 2D matrices such that the dimension
of the ``i`` th matrix is ``arr[i-1]*arr[i]``.
So suppose ``arr = [40, 20, 30, 10, 30]`` means we have ``4`` matrices of dimensions
``40*20``, ``20*30``, ``30*10`` and ``10*30``.

``matrix_chain_multiply()`` returns an integer denoting minimum number of
multiplications to multiply the chain.

We do not need to perform actual multiplication here.
We only need to decide the order in which to perform the multiplication.

Hints:
  1. Number of multiplications (ie cost) to multiply ``2`` matrices
     of size ``m*p`` and ``p*n`` is ``m*p*n``.
  2. Cost of matrix multiplication is not associative ie ``(M1*M2)*M3 != M1*(M2*M3)``
  3. Matrix multiplication is not commutative. So, ``M1*M2`` does not mean ``M2*M1``
     can be done.
  4. To determine the required order, we can try different combinations.

So, this problem has overlapping sub-problems and can be solved using recursion.
We use Dynamic Programming for optimal time complexity.

Example input:
    ``arr = [40, 20, 30, 10, 30]``
output:
    ``26000``
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache
from sys import maxsize


def matrix_chain_multiply(arr: list[int]) -> int:
    """
    Find the minimum number of multiplcations required to multiply the chain of matrices

    Args:
        `arr`: The input array of integers.

    Returns:
        Minimum number of multiplications needed to multiply the chain

    Examples:

    >>> matrix_chain_multiply([1, 2, 3, 4, 3])
    30
    >>> matrix_chain_multiply([10])
    0
    >>> matrix_chain_multiply([10, 20])
    0
    >>> matrix_chain_multiply([19, 2, 19])
    722
    >>> matrix_chain_multiply(list(range(1, 100)))
    323398
    >>> # matrix_chain_multiply(list(range(1, 251)))
    # 2626798
    """
    if len(arr) < 2:
        return 0
    # initialising 2D dp matrix
    n = len(arr)
    dp = [[maxsize for j in range(n)] for i in range(n)]
    # we want minimum cost of multiplication of matrices
    # of dimension (i*k) and (k*j). This cost is arr[i-1]*arr[k]*arr[j].
    for i in range(n - 1, 0, -1):
        for j in range(i, n):
            if i == j:
                dp[i][j] = 0
                continue
            for k in range(i, j):
                dp[i][j] = min(
                    dp[i][j], dp[i][k] + dp[k + 1][j] + arr[i - 1] * arr[k] * arr[j]
                )

    return dp[1][n - 1]


def matrix_chain_order(dims: list[int]) -> int:
    """
    Source: https://en.wikipedia.org/wiki/Matrix_chain_multiplication

    The dynamic programming solution is faster than cached the recursive solution and
    can handle larger inputs.

    >>> matrix_chain_order([1, 2, 3, 4, 3])
    30
    >>> matrix_chain_order([10])
    0
    >>> matrix_chain_order([10, 20])
    0
    >>> matrix_chain_order([19, 2, 19])
    722
    >>> matrix_chain_order(list(range(1, 100)))
    323398
    >>> # matrix_chain_order(list(range(1, 251)))  # Max before RecursionError is raised
    # 2626798
    """

    @cache
    def a(i: int, j: int) -> int:
        return min(
            (a(i, k) + dims[i] * dims[k] * dims[j] + a(k, j) for k in range(i + 1, j)),
            default=0,
        )

    return a(0, len(dims) - 1)


@contextmanager
def elapsed_time(msg: str) -> Iterator:
    # print(f"Starting: {msg}")
    from time import perf_counter_ns

    start = perf_counter_ns()
    yield
    print(f"Finished: {msg} in {(perf_counter_ns() - start) / 10**9} seconds.")


if __name__ == "__main__":
    import doctest

    doctest.testmod()
    with elapsed_time("matrix_chain_order"):
        print(f"{matrix_chain_order(list(range(1, 251))) = }")
    with elapsed_time("matrix_chain_multiply"):
        print(f"{matrix_chain_multiply(list(range(1, 251))) = }")
    with elapsed_time("matrix_chain_order"):
        print(f"{matrix_chain_order(list(range(1, 251))) = }")
    with elapsed_time("matrix_chain_multiply"):
        print(f"{matrix_chain_multiply(list(range(1, 251))) = }")


=================================================

"""
The maximum subarray sum problem is the task of finding the maximum sum that can be
obtained from a contiguous subarray within a given array of numbers. For example, given
the array [-2, 1, -3, 4, -1, 2, 1, -5, 4], the contiguous subarray with the maximum sum
is [4, -1, 2, 1], so the maximum subarray sum is 6.

Kadane's algorithm is a simple dynamic programming algorithm that solves the maximum
subarray sum problem in O(n) time and O(1) space.

Reference: https://en.wikipedia.org/wiki/Maximum_subarray_problem
"""

from collections.abc import Sequence


def max_subarray_sum(
    arr: Sequence[float], allow_empty_subarrays: bool = False
) -> float:
    """
    Solves the maximum subarray sum problem using Kadane's algorithm.
    :param arr: the given array of numbers
    :param allow_empty_subarrays: if True, then the algorithm considers empty subarrays

    >>> max_subarray_sum([2, 8, 9])
    19
    >>> max_subarray_sum([0, 0])
    0
    >>> max_subarray_sum([-1.0, 0.0, 1.0])
    1.0
    >>> max_subarray_sum([1, 2, 3, 4, -2])
    10
    >>> max_subarray_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4])
    6
    >>> max_subarray_sum([2, 3, -9, 8, -2])
    8
    >>> max_subarray_sum([-2, -3, -1, -4, -6])
    -1
    >>> max_subarray_sum([-2, -3, -1, -4, -6], allow_empty_subarrays=True)
    0
    >>> max_subarray_sum([])
    0
    """
    if not arr:
        return 0

    max_sum = 0 if allow_empty_subarrays else float("-inf")
    curr_sum = 0.0
    for num in arr:
        curr_sum = max(0 if allow_empty_subarrays else num, curr_sum + num)
        max_sum = max(max_sum, curr_sum)

    return max_sum


if __name__ == "__main__":
    from doctest import testmod

    testmod()

    nums = [-2, 1, -3, 4, -1, 2, 1, -5, 4]
    print(f"{max_subarray_sum(nums) = }")

=========================================

#!/usr/bin/env python3

# This Python program implements an optimal binary search tree (abbreviated BST)
# building dynamic programming algorithm that delivers O(n^2) performance.
#
# The goal of the optimal BST problem is to build a low-cost BST for a
# given set of nodes, each with its own key and frequency. The frequency
# of the node is defined as how many time the node is being searched.
# The search cost of binary search tree is given by this formula:
#
# cost(1, n) = sum{i = 1 to n}((depth(node_i) + 1) * node_i_freq)
#
# where n is number of nodes in the BST. The characteristic of low-cost
# BSTs is having a faster overall search time than other implementations.
# The reason for their fast search time is that the nodes with high
# frequencies will be placed near the root of the tree while the nodes
# with low frequencies will be placed near the leaves of the tree thus
# reducing search time in the most frequent instances.
import sys
from random import randint


class Node:
    """Binary Search Tree Node"""

    def __init__(self, key, freq):
        self.key = key
        self.freq = freq

    def __str__(self):
        """
        >>> str(Node(1, 2))
        'Node(key=1, freq=2)'
        """
        return f"Node(key={self.key}, freq={self.freq})"


def print_binary_search_tree(root, key, i, j, parent, is_left):
    """
    Recursive function to print a BST from a root table.

    >>> key = [3, 8, 9, 10, 17, 21]
    >>> root = [[0, 1, 1, 1, 1, 1], [0, 1, 1, 1, 1, 3], [0, 0, 2, 3, 3, 3], \
                [0, 0, 0, 3, 3, 3], [0, 0, 0, 0, 4, 5], [0, 0, 0, 0, 0, 5]]
    >>> print_binary_search_tree(root, key, 0, 5, -1, False)
    8 is the root of the binary search tree.
    3 is the left child of key 8.
    10 is the right child of key 8.
    9 is the left child of key 10.
    21 is the right child of key 10.
    17 is the left child of key 21.
    """
    if i > j or i < 0 or j > len(root) - 1:
        return

    node = root[i][j]
    if parent == -1:  # root does not have a parent
        print(f"{key[node]} is the root of the binary search tree.")
    elif is_left:
        print(f"{key[node]} is the left child of key {parent}.")
    else:
        print(f"{key[node]} is the right child of key {parent}.")

    print_binary_search_tree(root, key, i, node - 1, key[node], True)
    print_binary_search_tree(root, key, node + 1, j, key[node], False)


def find_optimal_binary_search_tree(nodes):
    """
    This function calculates and prints the optimal binary search tree.
    The dynamic programming algorithm below runs in O(n^2) time.
    Implemented from CLRS (Introduction to Algorithms) book.
    https://en.wikipedia.org/wiki/Introduction_to_Algorithms

    >>> find_optimal_binary_search_tree([Node(12, 8), Node(10, 34), Node(20, 50), \
                                         Node(42, 3), Node(25, 40), Node(37, 30)])
    Binary search tree nodes:
    Node(key=10, freq=34)
    Node(key=12, freq=8)
    Node(key=20, freq=50)
    Node(key=25, freq=40)
    Node(key=37, freq=30)
    Node(key=42, freq=3)
    <BLANKLINE>
    The cost of optimal BST for given tree nodes is 324.
    20 is the root of the binary search tree.
    10 is the left child of key 20.
    12 is the right child of key 10.
    25 is the right child of key 20.
    37 is the right child of key 25.
    42 is the right child of key 37.
    """
    # Tree nodes must be sorted first, the code below sorts the keys in
    # increasing order and rearrange its frequencies accordingly.
    nodes.sort(key=lambda node: node.key)

    n = len(nodes)

    keys = [nodes[i].key for i in range(n)]
    freqs = [nodes[i].freq for i in range(n)]

    # This 2D array stores the overall tree cost (which's as minimized as possible);
    # for a single key, cost is equal to frequency of the key.
    dp = [[freqs[i] if i == j else 0 for j in range(n)] for i in range(n)]
    # sum[i][j] stores the sum of key frequencies between i and j inclusive in nodes
    # array
    total = [[freqs[i] if i == j else 0 for j in range(n)] for i in range(n)]
    # stores tree roots that will be used later for constructing binary search tree
    root = [[i if i == j else 0 for j in range(n)] for i in range(n)]

    for interval_length in range(2, n + 1):
        for i in range(n - interval_length + 1):
            j = i + interval_length - 1

            dp[i][j] = sys.maxsize  # set the value to "infinity"
            total[i][j] = total[i][j - 1] + freqs[j]

            # Apply Knuth's optimization
            # Loop without optimization: for r in range(i, j + 1):
            for r in range(root[i][j - 1], root[i + 1][j] + 1):  # r is a temporal root
                left = dp[i][r - 1] if r != i else 0  # optimal cost for left subtree
                right = dp[r + 1][j] if r != j else 0  # optimal cost for right subtree
                cost = left + total[i][j] + right

                if dp[i][j] > cost:
                    dp[i][j] = cost
                    root[i][j] = r

    print("Binary search tree nodes:")
    for node in nodes:
        print(node)

    print(f"\nThe cost of optimal BST for given tree nodes is {dp[0][n - 1]}.")
    print_binary_search_tree(root, keys, 0, n - 1, -1, False)


def main():
    # A sample binary search tree
    nodes = [Node(i, randint(1, 50)) for i in range(10, 0, -1)]
    find_optimal_binary_search_tree(nodes)


if __name__ == "__main__":
    main()

=================================================

from typing import Any


def viterbi(
    observations_space: list,
    states_space: list,
    initial_probabilities: dict,
    transition_probabilities: dict,
    emission_probabilities: dict,
) -> list:
    """
    Viterbi Algorithm, to find the most likely path of
    states from the start and the expected output.

    https://en.wikipedia.org/wiki/Viterbi_algorithm

    Wikipedia example

    >>> observations = ["normal", "cold", "dizzy"]
    >>> states = ["Healthy", "Fever"]
    >>> start_p = {"Healthy": 0.6, "Fever": 0.4}
    >>> trans_p = {
    ...     "Healthy": {"Healthy": 0.7, "Fever": 0.3},
    ...     "Fever": {"Healthy": 0.4, "Fever": 0.6},
    ... }
    >>> emit_p = {
    ...     "Healthy": {"normal": 0.5, "cold": 0.4, "dizzy": 0.1},
    ...     "Fever": {"normal": 0.1, "cold": 0.3, "dizzy": 0.6},
    ... }
    >>> viterbi(observations, states, start_p, trans_p, emit_p)
    ['Healthy', 'Healthy', 'Fever']
    >>> viterbi((), states, start_p, trans_p, emit_p)
    Traceback (most recent call last):
        ...
    ValueError: There's an empty parameter
    >>> viterbi(observations, (), start_p, trans_p, emit_p)
    Traceback (most recent call last):
        ...
    ValueError: There's an empty parameter
    >>> viterbi(observations, states, {}, trans_p, emit_p)
    Traceback (most recent call last):
        ...
    ValueError: There's an empty parameter
    >>> viterbi(observations, states, start_p, {}, emit_p)
    Traceback (most recent call last):
        ...
    ValueError: There's an empty parameter
    >>> viterbi(observations, states, start_p, trans_p, {})
    Traceback (most recent call last):
        ...
    ValueError: There's an empty parameter
    >>> viterbi("invalid", states, start_p, trans_p, emit_p)
    Traceback (most recent call last):
        ...
    ValueError: observations_space must be a list
    >>> viterbi(["valid", 123], states, start_p, trans_p, emit_p)
    Traceback (most recent call last):
        ...
    ValueError: observations_space must be a list of strings
    >>> viterbi(observations, "invalid", start_p, trans_p, emit_p)
    Traceback (most recent call last):
        ...
    ValueError: states_space must be a list
    >>> viterbi(observations, ["valid", 123], start_p, trans_p, emit_p)
    Traceback (most recent call last):
        ...
    ValueError: states_space must be a list of strings
    >>> viterbi(observations, states, "invalid", trans_p, emit_p)
    Traceback (most recent call last):
        ...
    ValueError: initial_probabilities must be a dict
    >>> viterbi(observations, states, {2:2}, trans_p, emit_p)
    Traceback (most recent call last):
        ...
    ValueError: initial_probabilities all keys must be strings
    >>> viterbi(observations, states, {"a":2}, trans_p, emit_p)
    Traceback (most recent call last):
        ...
    ValueError: initial_probabilities all values must be float
    >>> viterbi(observations, states, start_p, "invalid", emit_p)
    Traceback (most recent call last):
        ...
    ValueError: transition_probabilities must be a dict
    >>> viterbi(observations, states, start_p, {"a":2}, emit_p)
    Traceback (most recent call last):
        ...
    ValueError: transition_probabilities all values must be dict
    >>> viterbi(observations, states, start_p, {2:{2:2}}, emit_p)
    Traceback (most recent call last):
        ...
    ValueError: transition_probabilities all keys must be strings
    >>> viterbi(observations, states, start_p, {"a":{2:2}}, emit_p)
    Traceback (most recent call last):
        ...
    ValueError: transition_probabilities all keys must be strings
    >>> viterbi(observations, states, start_p, {"a":{"b":2}}, emit_p)
    Traceback (most recent call last):
        ...
    ValueError: transition_probabilities nested dictionary all values must be float
    >>> viterbi(observations, states, start_p, trans_p, "invalid")
    Traceback (most recent call last):
        ...
    ValueError: emission_probabilities must be a dict
    >>> viterbi(observations, states, start_p, trans_p, None)
    Traceback (most recent call last):
        ...
    ValueError: There's an empty parameter

    """
    _validation(
        observations_space,
        states_space,
        initial_probabilities,
        transition_probabilities,
        emission_probabilities,
    )
    # Creates data structures and fill initial step
    probabilities: dict = {}
    pointers: dict = {}
    for state in states_space:
        observation = observations_space[0]
        probabilities[(state, observation)] = (
            initial_probabilities[state] * emission_probabilities[state][observation]
        )
        pointers[(state, observation)] = None

    # Fills the data structure with the probabilities of
    # different transitions and pointers to previous states
    for o in range(1, len(observations_space)):
        observation = observations_space[o]
        prior_observation = observations_space[o - 1]
        for state in states_space:
            # Calculates the argmax for probability function
            arg_max = ""
            max_probability = -1
            for k_state in states_space:
                probability = (
                    probabilities[(k_state, prior_observation)]
                    * transition_probabilities[k_state][state]
                    * emission_probabilities[state][observation]
                )
                if probability > max_probability:
                    max_probability = probability
                    arg_max = k_state

            # Update probabilities and pointers dicts
            probabilities[(state, observation)] = (
                probabilities[(arg_max, prior_observation)]
                * transition_probabilities[arg_max][state]
                * emission_probabilities[state][observation]
            )

            pointers[(state, observation)] = arg_max

    # The final observation
    final_observation = observations_space[len(observations_space) - 1]

    # argmax for given final observation
    arg_max = ""
    max_probability = -1
    for k_state in states_space:
        probability = probabilities[(k_state, final_observation)]
        if probability > max_probability:
            max_probability = probability
            arg_max = k_state
    last_state = arg_max

    # Process pointers backwards
    previous = last_state
    result = []
    for o in range(len(observations_space) - 1, -1, -1):
        result.append(previous)
        previous = pointers[previous, observations_space[o]]
    result.reverse()

    return result


def _validation(
    observations_space: Any,
    states_space: Any,
    initial_probabilities: Any,
    transition_probabilities: Any,
    emission_probabilities: Any,
) -> None:
    """
    >>> observations = ["normal", "cold", "dizzy"]
    >>> states = ["Healthy", "Fever"]
    >>> start_p = {"Healthy": 0.6, "Fever": 0.4}
    >>> trans_p = {
    ...     "Healthy": {"Healthy": 0.7, "Fever": 0.3},
    ...     "Fever": {"Healthy": 0.4, "Fever": 0.6},
    ... }
    >>> emit_p = {
    ...     "Healthy": {"normal": 0.5, "cold": 0.4, "dizzy": 0.1},
    ...     "Fever": {"normal": 0.1, "cold": 0.3, "dizzy": 0.6},
    ... }
    >>> _validation(observations, states, start_p, trans_p, emit_p)
    >>> _validation([], states, start_p, trans_p, emit_p)
    Traceback (most recent call last):
            ...
    ValueError: There's an empty parameter
    """
    _validate_not_empty(
        observations_space,
        states_space,
        initial_probabilities,
        transition_probabilities,
        emission_probabilities,
    )
    _validate_lists(observations_space, states_space)
    _validate_dicts(
        initial_probabilities, transition_probabilities, emission_probabilities
    )


def _validate_not_empty(
    observations_space: Any,
    states_space: Any,
    initial_probabilities: Any,
    transition_probabilities: Any,
    emission_probabilities: Any,
) -> None:
    """
    >>> _validate_not_empty(["a"], ["b"], {"c":0.5},
    ... {"d": {"e": 0.6}}, {"f": {"g": 0.7}})
    >>> _validate_not_empty(["a"], ["b"], {"c":0.5}, {}, {"f": {"g": 0.7}})
    Traceback (most recent call last):
            ...
    ValueError: There's an empty parameter
    >>> _validate_not_empty(["a"], ["b"], None, {"d": {"e": 0.6}}, {"f": {"g": 0.7}})
    Traceback (most recent call last):
            ...
    ValueError: There's an empty parameter
    """
    if not all(
        [
            observations_space,
            states_space,
            initial_probabilities,
            transition_probabilities,
            emission_probabilities,
        ]
    ):
        raise ValueError("There's an empty parameter")


def _validate_lists(observations_space: Any, states_space: Any) -> None:
    """
    >>> _validate_lists(["a"], ["b"])
    >>> _validate_lists(1234, ["b"])
    Traceback (most recent call last):
            ...
    ValueError: observations_space must be a list
    >>> _validate_lists(["a"], [3])
    Traceback (most recent call last):
            ...
    ValueError: states_space must be a list of strings
    """
    _validate_list(observations_space, "observations_space")
    _validate_list(states_space, "states_space")


def _validate_list(_object: Any, var_name: str) -> None:
    """
    >>> _validate_list(["a"], "mock_name")
    >>> _validate_list("a", "mock_name")
    Traceback (most recent call last):
            ...
    ValueError: mock_name must be a list
    >>> _validate_list([0.5], "mock_name")
    Traceback (most recent call last):
            ...
    ValueError: mock_name must be a list of strings
    """
    if not isinstance(_object, list):
        msg = f"{var_name} must be a list"
        raise ValueError(msg)
    else:
        for x in _object:
            if not isinstance(x, str):
                msg = f"{var_name} must be a list of strings"
                raise ValueError(msg)


def _validate_dicts(
    initial_probabilities: Any,
    transition_probabilities: Any,
    emission_probabilities: Any,
) -> None:
    """
    >>> _validate_dicts({"c":0.5}, {"d": {"e": 0.6}}, {"f": {"g": 0.7}})
    >>> _validate_dicts("invalid", {"d": {"e": 0.6}}, {"f": {"g": 0.7}})
    Traceback (most recent call last):
            ...
    ValueError: initial_probabilities must be a dict
    >>> _validate_dicts({"c":0.5}, {2: {"e": 0.6}}, {"f": {"g": 0.7}})
    Traceback (most recent call last):
            ...
    ValueError: transition_probabilities all keys must be strings
    >>> _validate_dicts({"c":0.5}, {"d": {"e": 0.6}}, {"f": {2: 0.7}})
    Traceback (most recent call last):
            ...
    ValueError: emission_probabilities all keys must be strings
    >>> _validate_dicts({"c":0.5}, {"d": {"e": 0.6}}, {"f": {"g": "h"}})
    Traceback (most recent call last):
            ...
    ValueError: emission_probabilities nested dictionary all values must be float
    """
    _validate_dict(initial_probabilities, "initial_probabilities", float)
    _validate_nested_dict(transition_probabilities, "transition_probabilities")
    _validate_nested_dict(emission_probabilities, "emission_probabilities")


def _validate_nested_dict(_object: Any, var_name: str) -> None:
    """
    >>> _validate_nested_dict({"a":{"b": 0.5}}, "mock_name")
    >>> _validate_nested_dict("invalid", "mock_name")
    Traceback (most recent call last):
            ...
    ValueError: mock_name must be a dict
    >>> _validate_nested_dict({"a": 8}, "mock_name")
    Traceback (most recent call last):
            ...
    ValueError: mock_name all values must be dict
    >>> _validate_nested_dict({"a":{2: 0.5}}, "mock_name")
    Traceback (most recent call last):
            ...
    ValueError: mock_name all keys must be strings
    >>> _validate_nested_dict({"a":{"b": 4}}, "mock_name")
    Traceback (most recent call last):
            ...
    ValueError: mock_name nested dictionary all values must be float
    """
    _validate_dict(_object, var_name, dict)
    for x in _object.values():
        _validate_dict(x, var_name, float, True)


def _validate_dict(
    _object: Any, var_name: str, value_type: type, nested: bool = False
) -> None:
    """
    >>> _validate_dict({"b": 0.5}, "mock_name", float)
    >>> _validate_dict("invalid", "mock_name", float)
    Traceback (most recent call last):
            ...
    ValueError: mock_name must be a dict
    >>> _validate_dict({"a": 8}, "mock_name", dict)
    Traceback (most recent call last):
            ...
    ValueError: mock_name all values must be dict
    >>> _validate_dict({2: 0.5}, "mock_name",float, True)
    Traceback (most recent call last):
            ...
    ValueError: mock_name all keys must be strings
    >>> _validate_dict({"b": 4}, "mock_name", float,True)
    Traceback (most recent call last):
            ...
    ValueError: mock_name nested dictionary all values must be float
    """
    if not isinstance(_object, dict):
        msg = f"{var_name} must be a dict"
        raise ValueError(msg)
    if not all(isinstance(x, str) for x in _object):
        msg = f"{var_name} all keys must be strings"
        raise ValueError(msg)
    if not all(isinstance(x, value_type) for x in _object.values()):
        nested_text = "nested dictionary " if nested else ""
        msg = f"{var_name} {nested_text}all values must be {value_type.__name__}"
        raise ValueError(msg)


if __name__ == "__main__":
    from doctest import testmod

    testmod()

=========================================


