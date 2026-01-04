import math


class SegmentTree:
    def __init__(self, a):
        self.A = a
        self.N = len(self.A)
        self.st = [0] * (
            4 * self.N
        )  # approximate the overall size of segment tree with array N
        if self.N:
            self.build(1, 0, self.N - 1)

    def left(self, idx):
        """
        Returns the left child index for a given index in a binary tree.

        >>> s = SegmentTree([1, 2, 3])
        >>> s.left(1)
        2
        >>> s.left(2)
        4
        """
        return idx * 2

    def right(self, idx):
        """
        Returns the right child index for a given index in a binary tree.

        >>> s = SegmentTree([1, 2, 3])
        >>> s.right(1)
        3
        >>> s.right(2)
        5
        """
        return idx * 2 + 1

    def build(self, idx, left, right):
        if left == right:
            self.st[idx] = self.A[left]
        else:
            mid = (left + right) // 2
            self.build(self.left(idx), left, mid)
            self.build(self.right(idx), mid + 1, right)
            self.st[idx] = max(self.st[self.left(idx)], self.st[self.right(idx)])

    def update(self, a, b, val):
        """
        Update the values in the segment tree in the range [a,b] with the given value.

        >>> s = SegmentTree([1, 2, 3, 4, 5])
        >>> s.update(2, 4, 10)
        True
        >>> s.query(1, 5)
        10
        """
        return self.update_recursive(1, 0, self.N - 1, a - 1, b - 1, val)

    def update_recursive(self, idx, left, right, a, b, val):
        """
        update(1, 1, N, a, b, v) for update val v to [a,b]
        """
        if right < a or left > b:
            return True
        if left == right:
            self.st[idx] = val
            return True
        mid = (left + right) // 2
        self.update_recursive(self.left(idx), left, mid, a, b, val)
        self.update_recursive(self.right(idx), mid + 1, right, a, b, val)
        self.st[idx] = max(self.st[self.left(idx)], self.st[self.right(idx)])
        return True

    def query(self, a, b):
        """
        Query the maximum value in the range [a,b].

        >>> s = SegmentTree([1, 2, 3, 4, 5])
        >>> s.query(1, 3)
        3
        >>> s.query(1, 5)
        5
        """
        return self.query_recursive(1, 0, self.N - 1, a - 1, b - 1)

    def query_recursive(self, idx, left, right, a, b):
        """
        query(1, 1, N, a, b) for query max of [a,b]
        """
        if right < a or left > b:
            return -math.inf
        if left >= a and right <= b:
            return self.st[idx]
        mid = (left + right) // 2
        q1 = self.query_recursive(self.left(idx), left, mid, a, b)
        q2 = self.query_recursive(self.right(idx), mid + 1, right, a, b)
        return max(q1, q2)

    def show_data(self):
        show_list = []
        for i in range(1, self.N + 1):
            show_list += [self.query(i, i)]
        print(show_list)


if __name__ == "__main__":
    A = [1, 2, -4, 7, 3, -5, 6, 11, -20, 9, 14, 15, 5, 2, -8]
    N = 15
    segt = SegmentTree(A)
    print(segt.query(4, 6))
    print(segt.query(7, 11))
    print(segt.query(7, 12))
    segt.update(1, 3, 111)
    print(segt.query(1, 15))
    segt.update(7, 8, 235)
    segt.show_data()

==========================

from copy import deepcopy


class FenwickTree:
    """
    Fenwick Tree

    More info: https://en.wikipedia.org/wiki/Fenwick_tree
    """

    def __init__(self, arr: list[int] | None = None, size: int | None = None) -> None:
        """
        Constructor for the Fenwick tree

        Parameters:
            arr (list): list of elements to initialize the tree with (optional)
            size (int): size of the Fenwick tree (if arr is None)
        """

        if arr is None and size is not None:
            self.size = size
            self.tree = [0] * size
        elif arr is not None:
            self.init(arr)
        else:
            raise ValueError("Either arr or size must be specified")

    def init(self, arr: list[int]) -> None:
        """
        Initialize the Fenwick tree with arr in O(N)

        Parameters:
            arr (list): list of elements to initialize the tree with

        Returns:
            None

        >>> a = [1, 2, 3, 4, 5]
        >>> f1 = FenwickTree(a)
        >>> f2 = FenwickTree(size=len(a))
        >>> for index, value in enumerate(a):
        ...     f2.add(index, value)
        >>> f1.tree == f2.tree
        True
        """
        self.size = len(arr)
        self.tree = deepcopy(arr)
        for i in range(1, self.size):
            j = self.next_(i)
            if j < self.size:
                self.tree[j] += self.tree[i]

    def get_array(self) -> list[int]:
        """
        Get the Normal Array of the Fenwick tree in O(N)

        Returns:
            list: Normal Array of the Fenwick tree

        >>> a = [i for i in range(128)]
        >>> f = FenwickTree(a)
        >>> f.get_array() == a
        True
        """
        arr = self.tree[:]
        for i in range(self.size - 1, 0, -1):
            j = self.next_(i)
            if j < self.size:
                arr[j] -= arr[i]
        return arr

    @staticmethod
    def next_(index: int) -> int:
        return index + (index & (-index))

    @staticmethod
    def prev(index: int) -> int:
        return index - (index & (-index))

    def add(self, index: int, value: int) -> None:
        """
        Add a value to index in O(lg N)

        Parameters:
            index (int): index to add value to
            value (int): value to add to index

        Returns:
            None

        >>> f = FenwickTree([1, 2, 3, 4, 5])
        >>> f.add(0, 1)
        >>> f.add(1, 2)
        >>> f.add(2, 3)
        >>> f.add(3, 4)
        >>> f.add(4, 5)
        >>> f.get_array()
        [2, 4, 6, 8, 10]
        """
        if index == 0:
            self.tree[0] += value
            return
        while index < self.size:
            self.tree[index] += value
            index = self.next_(index)

    def update(self, index: int, value: int) -> None:
        """
        Set the value of index in O(lg N)

        Parameters:
            index (int): index to set value to
            value (int): value to set in index

        Returns:
            None

        >>> f = FenwickTree([5, 4, 3, 2, 1])
        >>> f.update(0, 1)
        >>> f.update(1, 2)
        >>> f.update(2, 3)
        >>> f.update(3, 4)
        >>> f.update(4, 5)
        >>> f.get_array()
        [1, 2, 3, 4, 5]
        """
        self.add(index, value - self.get(index))

    def prefix(self, right: int) -> int:
        """
        Prefix sum of all elements in [0, right) in O(lg N)

        Parameters:
            right (int): right bound of the query (exclusive)

        Returns:
            int: sum of all elements in [0, right)

        >>> a = [i for i in range(128)]
        >>> f = FenwickTree(a)
        >>> res = True
        >>> for i in range(len(a)):
        ...     res = res and f.prefix(i) == sum(a[:i])
        >>> res
        True
        """
        if right == 0:
            return 0
        result = self.tree[0]
        right -= 1  # make right inclusive
        while right > 0:
            result += self.tree[right]
            right = self.prev(right)
        return result

    def query(self, left: int, right: int) -> int:
        """
        Query the sum of all elements in [left, right) in O(lg N)

        Parameters:
            left (int): left bound of the query (inclusive)
            right (int): right bound of the query (exclusive)

        Returns:
            int: sum of all elements in [left, right)

        >>> a = [i for i in range(128)]
        >>> f = FenwickTree(a)
        >>> res = True
        >>> for i in range(len(a)):
        ...     for j in range(i + 1, len(a)):
        ...         res = res and f.query(i, j) == sum(a[i:j])
        >>> res
        True
        """
        return self.prefix(right) - self.prefix(left)

    def get(self, index: int) -> int:
        """
        Get value at index in O(lg N)

        Parameters:
            index (int): index to get the value

        Returns:
            int: Value of element at index

        >>> a = [i for i in range(128)]
        >>> f = FenwickTree(a)
        >>> res = True
        >>> for i in range(len(a)):
        ...     res = res and f.get(i) == a[i]
        >>> res
        True
        """
        return self.query(index, index + 1)

    def rank_query(self, value: int) -> int:
        """
        Find the largest index with prefix(i) <= value in O(lg N)
        NOTE: Requires that all values are non-negative!

        Parameters:
            value (int): value to find the largest index of

        Returns:
            -1: if value is smaller than all elements in prefix sum
            int: largest index with prefix(i) <= value

        >>> f = FenwickTree([1, 2, 0, 3, 0, 5])
        >>> f.rank_query(0)
        -1
        >>> f.rank_query(2)
        0
        >>> f.rank_query(1)
        0
        >>> f.rank_query(3)
        2
        >>> f.rank_query(5)
        2
        >>> f.rank_query(6)
        4
        >>> f.rank_query(11)
        5
        """
        value -= self.tree[0]
        if value < 0:
            return -1

        j = 1  # Largest power of 2 <= size
        while j * 2 < self.size:
            j *= 2

        i = 0

        while j > 0:
            if i + j < self.size and self.tree[i + j] <= value:
                value -= self.tree[i + j]
                i += j
            j //= 2
        return i


if __name__ == "__main__":
    import doctest

    doctest.testmod()

=====================================

from __future__ import annotations

from random import random


class Node:
    """
    Treap's node
    Treap is a binary tree by value and heap by priority
    """

    def __init__(self, value: int | None = None):
        self.value = value
        self.prior = random()
        self.left: Node | None = None
        self.right: Node | None = None

    def __repr__(self) -> str:
        from pprint import pformat

        if self.left is None and self.right is None:
            return f"'{self.value}: {self.prior:.5}'"
        else:
            return pformat(
                {f"{self.value}: {self.prior:.5}": (self.left, self.right)}, indent=1
            )

    def __str__(self) -> str:
        value = str(self.value) + " "
        left = str(self.left or "")
        right = str(self.right or "")
        return value + left + right


def split(root: Node | None, value: int) -> tuple[Node | None, Node | None]:
    """
    We split current tree into 2 trees with value:

    Left tree contains all values less than split value.
    Right tree contains all values greater or equal, than split value
    """
    if root is None or root.value is None:  # None tree is split into 2 Nones
        return None, None
    elif value < root.value:
        """
        Right tree's root will be current node.
        Now we split(with the same value) current node's left son
        Left tree: left part of that split
        Right tree's left son: right part of that split
        """
        left, root.left = split(root.left, value)
        return left, root
    else:
        """
        Just symmetric to previous case
        """
        root.right, right = split(root.right, value)
        return root, right


def merge(left: Node | None, right: Node | None) -> Node | None:
    """
    We merge 2 trees into one.
    Note: all left tree's values must be less than all right tree's
    """
    if (not left) or (not right):  # If one node is None, return the other
        return left or right
    elif left.prior < right.prior:
        """
        Left will be root because it has more priority
        Now we need to merge left's right son and right tree
        """
        left.right = merge(left.right, right)
        return left
    else:
        """
        Symmetric as well
        """
        right.left = merge(left, right.left)
        return right


def insert(root: Node | None, value: int) -> Node | None:
    """
    Insert element

    Split current tree with a value into left, right,
    Insert new node into the middle
    Merge left, node, right into root
    """
    node = Node(value)
    left, right = split(root, value)
    return merge(merge(left, node), right)


def erase(root: Node | None, value: int) -> Node | None:
    """
    Erase element

    Split all nodes with values less into left,
    Split all nodes with values greater into right.
    Merge left, right
    """
    left, right = split(root, value - 1)
    _, right = split(right, value)
    return merge(left, right)


def inorder(root: Node | None) -> None:
    """
    Just recursive print of a tree
    """
    if not root:  # None
        return
    else:
        inorder(root.left)
        print(root.value, end=",")
        inorder(root.right)


def interact_treap(root: Node | None, args: str) -> Node | None:
    """
    Commands:
    + value to add value into treap
    - value to erase all nodes with value

        >>> root = interact_treap(None, "+1")
        >>> inorder(root)
        1,
        >>> root = interact_treap(root, "+3 +5 +17 +19 +2 +16 +4 +0")
        >>> inorder(root)
        0,1,2,3,4,5,16,17,19,
        >>> root = interact_treap(root, "+4 +4 +4")
        >>> inorder(root)
        0,1,2,3,4,4,4,4,5,16,17,19,
        >>> root = interact_treap(root, "-0")
        >>> inorder(root)
        1,2,3,4,4,4,4,5,16,17,19,
        >>> root = interact_treap(root, "-4")
        >>> inorder(root)
        1,2,3,5,16,17,19,
        >>> root = interact_treap(root, "=0")
        Unknown command
    """
    for arg in args.split():
        if arg[0] == "+":
            root = insert(root, int(arg[1:]))

        elif arg[0] == "-":
            root = erase(root, int(arg[1:]))

        else:
            print("Unknown command")

    return root


def main() -> None:
    """After each command, program prints treap"""
    root = None
    print(
        "enter numbers to create a tree, + value to add value into treap, "
        "- value to erase all nodes with value. 'q' to quit. "
    )

    args = input()
    while args != "q":
        root = interact_treap(root, args)
        print(root)
        args = input()

    print("good by!")


if __name__ == "__main__":
    import doctest

    doctest.testmod()
    main()

==========================================

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterable
from typing import Protocol, TypeVar


class Comparable(Protocol):
    @abstractmethod
    def __lt__(self: T, other: T) -> bool:
        pass

    @abstractmethod
    def __gt__(self: T, other: T) -> bool:
        pass

    @abstractmethod
    def __eq__(self: T, other: object) -> bool:
        pass


T = TypeVar("T", bound=Comparable)


class Heap[T: Comparable]:
    """A Max Heap Implementation

    >>> unsorted = [103, 9, 1, 7, 11, 15, 25, 201, 209, 107, 5]
    >>> h = Heap()
    >>> h.build_max_heap(unsorted)
    >>> h
    [209, 201, 25, 103, 107, 15, 1, 9, 7, 11, 5]
    >>>
    >>> h.extract_max()
    209
    >>> h
    [201, 107, 25, 103, 11, 15, 1, 9, 7, 5]
    >>>
    >>> h.insert(100)
    >>> h
    [201, 107, 25, 103, 100, 15, 1, 9, 7, 5, 11]
    >>>
    >>> h.heap_sort()
    >>> h
    [1, 5, 7, 9, 11, 15, 25, 100, 103, 107, 201]
    """

    def __init__(self) -> None:
        self.h: list[T] = []
        self.heap_size: int = 0

    def __repr__(self) -> str:
        return str(self.h)

    def parent_index(self, child_idx: int) -> int | None:
        """
        returns the parent index based on the given child index

        >>> h = Heap()
        >>> h.build_max_heap([103, 9, 1, 7, 11, 15, 25, 201, 209, 107, 5])
        >>> h
        [209, 201, 25, 103, 107, 15, 1, 9, 7, 11, 5]

        >>> h.parent_index(-1)  # returns none if index is <=0

        >>> h.parent_index(0)   # returns none if index is <=0

        >>> h.parent_index(1)
        0
        >>> h.parent_index(2)
        0
        >>> h.parent_index(3)
        1
        >>> h.parent_index(4)
        1
        >>> h.parent_index(5)
        2
        >>> h.parent_index(10.5)
        4.0
        >>> h.parent_index(209.0)
        104.0
        >>> h.parent_index("Test")
        Traceback (most recent call last):
        ...
        TypeError: '>' not supported between instances of 'str' and 'int'
        """
        if child_idx > 0:
            return (child_idx - 1) // 2
        return None

    def left_child_idx(self, parent_idx: int) -> int | None:
        """
        return the left child index if the left child exists.
        if not, return None.
        """
        left_child_index = 2 * parent_idx + 1
        if left_child_index < self.heap_size:
            return left_child_index
        return None

    def right_child_idx(self, parent_idx: int) -> int | None:
        """
        return the right child index if the right child exists.
        if not, return None.
        """
        right_child_index = 2 * parent_idx + 2
        if right_child_index < self.heap_size:
            return right_child_index
        return None

    def max_heapify(self, index: int) -> None:
        """
        correct a single violation of the heap property in a subtree's root.

        It is the function that is responsible for restoring the property
        of Max heap i.e the maximum element is always at top.
        """
        if index < self.heap_size:
            violation: int = index
            left_child = self.left_child_idx(index)
            right_child = self.right_child_idx(index)
            # check which child is larger than its parent
            if left_child is not None and self.h[left_child] > self.h[violation]:
                violation = left_child
            if right_child is not None and self.h[right_child] > self.h[violation]:
                violation = right_child
            # if violation indeed exists
            if violation != index:
                # swap to fix the violation
                self.h[violation], self.h[index] = self.h[index], self.h[violation]
                # fix the subsequent violation recursively if any
                self.max_heapify(violation)

    def build_max_heap(self, collection: Iterable[T]) -> None:
        """
        build max heap from an unsorted array

        >>> h = Heap()
        >>> h.build_max_heap([20,40,50,20,10])
        >>> h
        [50, 40, 20, 20, 10]

        >>> h = Heap()
        >>> h.build_max_heap([1,2,3,4,5,6,7,8,9,0])
        >>> h
        [9, 8, 7, 4, 5, 6, 3, 2, 1, 0]

        >>> h = Heap()
        >>> h.build_max_heap([514,5,61,57,8,99,105])
        >>> h
        [514, 57, 105, 5, 8, 99, 61]

        >>> h = Heap()
        >>> h.build_max_heap([514,5,61.6,57,8,9.9,105])
        >>> h
        [514, 57, 105, 5, 8, 9.9, 61.6]
        """
        self.h = list(collection)
        self.heap_size = len(self.h)
        if self.heap_size > 1:
            # max_heapify from right to left but exclude leaves (last level)
            for i in range(self.heap_size // 2 - 1, -1, -1):
                self.max_heapify(i)

    def extract_max(self) -> T:
        """
        get and remove max from heap

        >>> h = Heap()
        >>> h.build_max_heap([20,40,50,20,10])
        >>> h.extract_max()
        50

        >>> h = Heap()
        >>> h.build_max_heap([514,5,61,57,8,99,105])
        >>> h.extract_max()
        514

        >>> h = Heap()
        >>> h.build_max_heap([1,2,3,4,5,6,7,8,9,0])
        >>> h.extract_max()
        9
        """
        if self.heap_size >= 2:
            me = self.h[0]
            self.h[0] = self.h.pop(-1)
            self.heap_size -= 1
            self.max_heapify(0)
            return me
        elif self.heap_size == 1:
            self.heap_size -= 1
            return self.h.pop(-1)
        else:
            raise Exception("Empty heap")

    def insert(self, value: T) -> None:
        """
        insert a new value into the max heap

        >>> h = Heap()
        >>> h.insert(10)
        >>> h
        [10]

        >>> h = Heap()
        >>> h.insert(10)
        >>> h.insert(10)
        >>> h
        [10, 10]

        >>> h = Heap()
        >>> h.insert(10)
        >>> h.insert(10.1)
        >>> h
        [10.1, 10]

        >>> h = Heap()
        >>> h.insert(0.1)
        >>> h.insert(0)
        >>> h.insert(9)
        >>> h.insert(5)
        >>> h
        [9, 5, 0.1, 0]
        """
        self.h.append(value)
        idx = (self.heap_size - 1) // 2
        self.heap_size += 1
        while idx >= 0:
            self.max_heapify(idx)
            idx = (idx - 1) // 2

    def heap_sort(self) -> None:
        size = self.heap_size
        for j in range(size - 1, 0, -1):
            self.h[0], self.h[j] = self.h[j], self.h[0]
            self.heap_size -= 1
            self.max_heapify(0)
        self.heap_size = size


if __name__ == "__main__":
    import doctest

    # run doc test
    doctest.testmod()

    # demo
    for unsorted in [
        [0],
        [2],
        [3, 5],
        [5, 3],
        [5, 5],
        [0, 0, 0, 0],
        [1, 1, 1, 1],
        [2, 2, 3, 5],
        [0, 2, 2, 3, 5],
        [2, 5, 3, 0, 2, 3, 0, 3],
        [6, 1, 2, 7, 9, 3, 4, 5, 10, 8],
        [103, 9, 1, 7, 11, 15, 25, 201, 209, 107, 5],
        [-45, -2, -5],
    ]:
        print(f"unsorted array: {unsorted}")

        heap: Heap[int] = Heap()
        heap.build_max_heap(unsorted)
        print(f"after build heap: {heap}")

        print(f"max value: {heap.extract_max()}")
        print(f"after max value removed: {heap}")

        heap.insert(100)
        print(f"after new value 100 inserted: {heap}")

        heap.heap_sort()
        print(f"heap-sorted array: {heap}\n")

==================================

#!/usr/bin/env python3

from __future__ import annotations

import random
from collections.abc import Iterable
from typing import Any, TypeVar

T = TypeVar("T", bound=bool)


class RandomizedHeapNode[T: bool]:
    """
    One node of the randomized heap. Contains the value and references to
    two children.
    """

    def __init__(self, value: T) -> None:
        self._value: T = value
        self.left: RandomizedHeapNode[T] | None = None
        self.right: RandomizedHeapNode[T] | None = None

    @property
    def value(self) -> T:
        """
        Return the value of the node.

        >>> rhn = RandomizedHeapNode(10)
        >>> rhn.value
        10
        >>> rhn = RandomizedHeapNode(-10)
        >>> rhn.value
        -10
        """
        return self._value

    @staticmethod
    def merge(
        root1: RandomizedHeapNode[T] | None, root2: RandomizedHeapNode[T] | None
    ) -> RandomizedHeapNode[T] | None:
        """
        Merge 2 nodes together.

        >>> rhn1 = RandomizedHeapNode(10)
        >>> rhn2 = RandomizedHeapNode(20)
        >>> RandomizedHeapNode.merge(rhn1, rhn2).value
        10

        >>> rhn1 = RandomizedHeapNode(20)
        >>> rhn2 = RandomizedHeapNode(10)
        >>> RandomizedHeapNode.merge(rhn1, rhn2).value
        10

        >>> rhn1 = RandomizedHeapNode(5)
        >>> rhn2 = RandomizedHeapNode(0)
        >>> RandomizedHeapNode.merge(rhn1, rhn2).value
        0
        """
        if not root1:
            return root2

        if not root2:
            return root1

        if root1.value > root2.value:
            root1, root2 = root2, root1

        if random.choice([True, False]):
            root1.left, root1.right = root1.right, root1.left

        root1.left = RandomizedHeapNode.merge(root1.left, root2)

        return root1


class RandomizedHeap[T: bool]:
    """
    A data structure that allows inserting a new value and to pop the smallest
    values. Both operations take O(logN) time where N is the size of the
    structure.
    Wiki: https://en.wikipedia.org/wiki/Randomized_meldable_heap

    >>> RandomizedHeap([2, 3, 1, 5, 1, 7]).to_sorted_list()
    [1, 1, 2, 3, 5, 7]

    >>> rh = RandomizedHeap()
    >>> rh.pop()
    Traceback (most recent call last):
        ...
    IndexError: Can't get top element for the empty heap.

    >>> rh.insert(1)
    >>> rh.insert(-1)
    >>> rh.insert(0)
    >>> rh.to_sorted_list()
    [-1, 0, 1]
    """

    def __init__(self, data: Iterable[T] | None = ()) -> None:
        """
        >>> rh = RandomizedHeap([3, 1, 3, 7])
        >>> rh.to_sorted_list()
        [1, 3, 3, 7]
        """
        self._root: RandomizedHeapNode[T] | None = None

        if data:
            for item in data:
                self.insert(item)

    def insert(self, value: T) -> None:
        """
        Insert the value into the heap.

        >>> rh = RandomizedHeap()
        >>> rh.insert(3)
        >>> rh.insert(1)
        >>> rh.insert(3)
        >>> rh.insert(7)
        >>> rh.to_sorted_list()
        [1, 3, 3, 7]
        """
        self._root = RandomizedHeapNode.merge(self._root, RandomizedHeapNode(value))

    def pop(self) -> T | None:
        """
        Pop the smallest value from the heap and return it.

        >>> rh = RandomizedHeap([3, 1, 3, 7])
        >>> rh.pop()
        1
        >>> rh.pop()
        3
        >>> rh.pop()
        3
        >>> rh.pop()
        7
        >>> rh.pop()
        Traceback (most recent call last):
            ...
        IndexError: Can't get top element for the empty heap.
        """

        result = self.top()

        if self._root is None:
            return None

        self._root = RandomizedHeapNode.merge(self._root.left, self._root.right)

        return result

    def top(self) -> T:
        """
        Return the smallest value from the heap.

        >>> rh = RandomizedHeap()
        >>> rh.insert(3)
        >>> rh.top()
        3
        >>> rh.insert(1)
        >>> rh.top()
        1
        >>> rh.insert(3)
        >>> rh.top()
        1
        >>> rh.insert(7)
        >>> rh.top()
        1
        """
        if not self._root:
            raise IndexError("Can't get top element for the empty heap.")
        return self._root.value

    def clear(self) -> None:
        """
        Clear the heap.

        >>> rh = RandomizedHeap([3, 1, 3, 7])
        >>> rh.clear()
        >>> rh.pop()
        Traceback (most recent call last):
            ...
        IndexError: Can't get top element for the empty heap.
        """
        self._root = None

    def to_sorted_list(self) -> list[Any]:
        """
        Returns sorted list containing all the values in the heap.

        >>> rh = RandomizedHeap([3, 1, 3, 7])
        >>> rh.to_sorted_list()
        [1, 3, 3, 7]
        """
        result = []
        while self:
            result.append(self.pop())

        return result

    def __bool__(self) -> bool:
        """
        Check if the heap is not empty.

        >>> rh = RandomizedHeap()
        >>> bool(rh)
        False
        >>> rh.insert(1)
        >>> bool(rh)
        True
        >>> rh.clear()
        >>> bool(rh)
        False
        """
        return self._root is not None


if __name__ == "__main__":
    import doctest

    doctest.testmod()

==================================

"""
Binomial Heap
Reference: Advanced Data Structures, Peter Brass
"""


class Node:
    """
    Node in a doubly-linked binomial tree, containing:
        - value
        - size of left subtree
        - link to left, right and parent nodes
    """

    def __init__(self, val):
        self.val = val
        # Number of nodes in left subtree
        self.left_tree_size = 0
        self.left = None
        self.right = None
        self.parent = None

    def merge_trees(self, other):
        """
        In-place merge of two binomial trees of equal size.
        Returns the root of the resulting tree
        """
        assert self.left_tree_size == other.left_tree_size, "Unequal Sizes of Blocks"

        if self.val < other.val:
            other.left = self.right
            other.parent = None
            if self.right:
                self.right.parent = other
            self.right = other
            self.left_tree_size = self.left_tree_size * 2 + 1
            return self
        else:
            self.left = other.right
            self.parent = None
            if other.right:
                other.right.parent = self
            other.right = self
            other.left_tree_size = other.left_tree_size * 2 + 1
            return other


class BinomialHeap:
    r"""
    Min-oriented priority queue implemented with the Binomial Heap data
    structure implemented with the BinomialHeap class. It supports:
        - Insert element in a heap with n elements: Guaranteed logn, amoratized 1
        - Merge (meld) heaps of size m and n: O(logn + logm)
        - Delete Min: O(logn)
        - Peek (return min without deleting it): O(1)

    Example:

    Create a random permutation of 30 integers to be inserted and 19 of them deleted
    >>> import numpy as np
    >>> permutation = np.random.permutation(list(range(30)))

    Create a Heap and insert the 30 integers
    __init__() test
    >>> first_heap = BinomialHeap()

    30 inserts - insert() test
    >>> for number in permutation:
    ...     first_heap.insert(number)

    Size test
    >>> first_heap.size
    30

    Deleting - delete() test
    >>> [int(first_heap.delete_min()) for _ in range(20)]
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

    Create a new Heap
    >>> second_heap = BinomialHeap()
    >>> vals = [17, 20, 31, 34]
    >>> for value in vals:
    ...     second_heap.insert(value)


    The heap should have the following structure:

                    17
                   /  \
                  #    31
                      /  \
                    20    34
                   /  \  /  \
                  #    # #   #

    preOrder() test
    >>> " ".join(str(x) for x in second_heap.pre_order())
    "(17, 0) ('#', 1) (31, 1) (20, 2) ('#', 3) ('#', 3) (34, 2) ('#', 3) ('#', 3)"

    printing Heap - __str__() test
    >>> print(second_heap)
    17
    -#
    -31
    --20
    ---#
    ---#
    --34
    ---#
    ---#

    mergeHeaps() test
    >>>
    >>> merged = second_heap.merge_heaps(first_heap)
    >>> merged.peek()
    17

    values in merged heap; (merge is inplace)
    >>> results = []
    >>> while not first_heap.is_empty():
    ...     results.append(int(first_heap.delete_min()))
    >>> results
    [17, 20, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 31, 34]
    """

    def __init__(self, bottom_root=None, min_node=None, heap_size=0):
        self.size = heap_size
        self.bottom_root = bottom_root
        self.min_node = min_node

    def merge_heaps(self, other):
        """
        In-place merge of two binomial heaps.
        Both of them become the resulting merged heap
        """

        # Empty heaps corner cases
        if other.size == 0:
            return None
        if self.size == 0:
            self.size = other.size
            self.bottom_root = other.bottom_root
            self.min_node = other.min_node
            return None
        # Update size
        self.size = self.size + other.size

        # Update min.node
        if self.min_node.val > other.min_node.val:
            self.min_node = other.min_node
        # Merge

        # Order roots by left_subtree_size
        combined_roots_list = []
        i, j = self.bottom_root, other.bottom_root
        while i or j:
            if i and ((not j) or i.left_tree_size < j.left_tree_size):
                combined_roots_list.append((i, True))
                i = i.parent
            else:
                combined_roots_list.append((j, False))
                j = j.parent
        # Insert links between them
        for i in range(len(combined_roots_list) - 1):
            if combined_roots_list[i][1] != combined_roots_list[i + 1][1]:
                combined_roots_list[i][0].parent = combined_roots_list[i + 1][0]
                combined_roots_list[i + 1][0].left = combined_roots_list[i][0]
        # Consecutively merge roots with same left_tree_size
        i = combined_roots_list[0][0]
        while i.parent:
            if (
                (i.left_tree_size == i.parent.left_tree_size) and (not i.parent.parent)
            ) or (
                i.left_tree_size == i.parent.left_tree_size
                and i.left_tree_size != i.parent.parent.left_tree_size
            ):
                # Neighbouring Nodes
                previous_node = i.left
                next_node = i.parent.parent

                # Merging trees
                i = i.merge_trees(i.parent)

                # Updating links
                i.left = previous_node
                i.parent = next_node
                if previous_node:
                    previous_node.parent = i
                if next_node:
                    next_node.left = i
            else:
                i = i.parent
        # Updating self.bottom_root
        while i.left:
            i = i.left
        self.bottom_root = i

        # Update other
        other.size = self.size
        other.bottom_root = self.bottom_root
        other.min_node = self.min_node

        # Return the merged heap
        return self

    def insert(self, val):
        """
        insert a value in the heap
        """
        if self.size == 0:
            self.bottom_root = Node(val)
            self.size = 1
            self.min_node = self.bottom_root
        else:
            # Create new node
            new_node = Node(val)

            # Update size
            self.size += 1

            # update min_node
            if val < self.min_node.val:
                self.min_node = new_node
            # Put new_node as a bottom_root in heap
            self.bottom_root.left = new_node
            new_node.parent = self.bottom_root
            self.bottom_root = new_node

            # Consecutively merge roots with same left_tree_size
            while (
                self.bottom_root.parent
                and self.bottom_root.left_tree_size
                == self.bottom_root.parent.left_tree_size
            ):
                # Next node
                next_node = self.bottom_root.parent.parent

                # Merge
                self.bottom_root = self.bottom_root.merge_trees(self.bottom_root.parent)

                # Update Links
                self.bottom_root.parent = next_node
                self.bottom_root.left = None
                if next_node:
                    next_node.left = self.bottom_root

    def peek(self):
        """
        return min element without deleting it
        """
        return self.min_node.val

    def is_empty(self):
        return self.size == 0

    def delete_min(self):
        """
        delete min element and return it
        """
        # assert not self.isEmpty(), "Empty Heap"

        # Save minimal value
        min_value = self.min_node.val

        # Last element in heap corner case
        if self.size == 1:
            # Update size
            self.size = 0

            # Update bottom root
            self.bottom_root = None

            # Update min_node
            self.min_node = None

            return min_value
        # No right subtree corner case
        # The structure of the tree implies that this should be the bottom root
        # and there is at least one other root
        if self.min_node.right is None:
            # Update size
            self.size -= 1

            # Update bottom root
            self.bottom_root = self.bottom_root.parent
            self.bottom_root.left = None

            # Update min_node
            self.min_node = self.bottom_root
            i = self.bottom_root.parent
            while i:
                if i.val < self.min_node.val:
                    self.min_node = i
                i = i.parent
            return min_value
        # General case
        # Find the BinomialHeap of the right subtree of min_node
        bottom_of_new = self.min_node.right
        bottom_of_new.parent = None
        min_of_new = bottom_of_new
        size_of_new = 1

        # Size, min_node and bottom_root
        while bottom_of_new.left:
            size_of_new = size_of_new * 2 + 1
            bottom_of_new = bottom_of_new.left
            if bottom_of_new.val < min_of_new.val:
                min_of_new = bottom_of_new
        # Corner case of single root on top left path
        if (not self.min_node.left) and (not self.min_node.parent):
            self.size = size_of_new
            self.bottom_root = bottom_of_new
            self.min_node = min_of_new
            # print("Single root, multiple nodes case")
            return min_value
        # Remaining cases
        # Construct heap of right subtree
        new_heap = BinomialHeap(
            bottom_root=bottom_of_new, min_node=min_of_new, heap_size=size_of_new
        )

        # Update size
        self.size = self.size - 1 - size_of_new

        # Neighbour nodes
        previous_node = self.min_node.left
        next_node = self.min_node.parent

        # Initialize new bottom_root and min_node
        self.min_node = previous_node or next_node
        self.bottom_root = next_node

        # Update links of previous_node and search below for new min_node and
        # bottom_root
        if previous_node:
            previous_node.parent = next_node

            # Update bottom_root and search for min_node below
            self.bottom_root = previous_node
            self.min_node = previous_node
            while self.bottom_root.left:
                self.bottom_root = self.bottom_root.left
                if self.bottom_root.val < self.min_node.val:
                    self.min_node = self.bottom_root
        if next_node:
            next_node.left = previous_node

            # Search for new min_node above min_node
            i = next_node
            while i:
                if i.val < self.min_node.val:
                    self.min_node = i
                i = i.parent
        # Merge heaps
        self.merge_heaps(new_heap)

        return int(min_value)

    def pre_order(self):
        """
        Returns the Pre-order representation of the heap including
        values of nodes plus their level distance from the root;
        Empty nodes appear as #
        """
        # Find top root
        top_root = self.bottom_root
        while top_root.parent:
            top_root = top_root.parent
        # preorder
        heap_pre_order = []
        self.__traversal(top_root, heap_pre_order)
        return heap_pre_order

    def __traversal(self, curr_node, preorder, level=0):
        """
        Pre-order traversal of nodes
        """
        if curr_node:
            preorder.append((curr_node.val, level))
            self.__traversal(curr_node.left, preorder, level + 1)
            self.__traversal(curr_node.right, preorder, level + 1)
        else:
            preorder.append(("#", level))

    def __str__(self):
        """
        Overwriting str for a pre-order print of nodes in heap;
        Performance is poor, so use only for small examples
        """
        if self.is_empty():
            return ""
        preorder_heap = self.pre_order()

        return "\n".join(("-" * level + str(value)) for value, level in preorder_heap)


# Unit Tests
if __name__ == "__main__":
    import doctest

    doctest.testmod()

===================================

"""
See https://en.wikipedia.org/wiki/Bloom_filter

The use of this data structure is to test membership in a set.
Compared to Python's built-in set() it is more space-efficient.
In the following example, only 8 bits of memory will be used:
>>> bloom = Bloom(size=8)

Initially, the filter contains all zeros:
>>> bloom.bitstring
'00000000'

When an element is added, two bits are set to 1
since there are 2 hash functions in this implementation:
>>> "Titanic" in bloom
False
>>> bloom.add("Titanic")
>>> bloom.bitstring
'01100000'
>>> "Titanic" in bloom
True

However, sometimes only one bit is added
because both hash functions return the same value
>>> bloom.add("Avatar")
>>> "Avatar" in bloom
True
>>> bloom.format_hash("Avatar")
'00000100'
>>> bloom.bitstring
'01100100'

Not added elements should return False ...
>>> not_present_films = ("The Godfather", "Interstellar", "Parasite", "Pulp Fiction")
>>> {
...   film: bloom.format_hash(film) for film in not_present_films
... } # doctest: +NORMALIZE_WHITESPACE
{'The Godfather': '00000101',
 'Interstellar': '00000011',
 'Parasite': '00010010',
 'Pulp Fiction': '10000100'}
>>> any(film in bloom for film in not_present_films)
False

but sometimes there are false positives:
>>> "Ratatouille" in bloom
True
>>> bloom.format_hash("Ratatouille")
'01100000'

The probability increases with the number of elements added.
The probability decreases with the number of bits in the bitarray.
>>> bloom.estimated_error_rate
0.140625
>>> bloom.add("The Godfather")
>>> bloom.estimated_error_rate
0.25
>>> bloom.bitstring
'01100101'
"""

from hashlib import md5, sha256

HASH_FUNCTIONS = (sha256, md5)


class Bloom:
    def __init__(self, size: int = 8) -> None:
        self.bitarray = 0b0
        self.size = size

    def add(self, value: str) -> None:
        h = self.hash_(value)
        self.bitarray |= h

    def exists(self, value: str) -> bool:
        h = self.hash_(value)
        return (h & self.bitarray) == h

    def __contains__(self, other: str) -> bool:
        return self.exists(other)

    def format_bin(self, bitarray: int) -> str:
        res = bin(bitarray)[2:]
        return res.zfill(self.size)

    @property
    def bitstring(self) -> str:
        return self.format_bin(self.bitarray)

    def hash_(self, value: str) -> int:
        res = 0b0
        for func in HASH_FUNCTIONS:
            position = (
                int.from_bytes(func(value.encode()).digest(), "little") % self.size
            )
            res |= 2**position
        return res

    def format_hash(self, value: str) -> str:
        return self.format_bin(self.hash_(value))

    @property
    def estimated_error_rate(self) -> float:
        n_ones = bin(self.bitarray).count("1")
        return (n_ones / self.size) ** len(HASH_FUNCTIONS)

============================

"""
Hash map with open addressing.

https://en.wikipedia.org/wiki/Hash_table

Another hash map implementation, with a good explanation.
Modern Dictionaries by Raymond Hettinger
https://www.youtube.com/watch?v=p33CVV29OG8
"""

from collections.abc import Iterator, MutableMapping
from dataclasses import dataclass
from typing import TypeVar

KEY = TypeVar("KEY")
VAL = TypeVar("VAL")


@dataclass(slots=True)
class _Item[KEY, VAL]:
    key: KEY
    val: VAL


class _DeletedItem(_Item):
    def __init__(self) -> None:
        super().__init__(None, None)

    def __bool__(self) -> bool:
        return False


_deleted = _DeletedItem()


class HashMap(MutableMapping[KEY, VAL]):
    """
    Hash map with open addressing.
    """

    def __init__(
        self, initial_block_size: int = 8, capacity_factor: float = 0.75
    ) -> None:
        self._initial_block_size = initial_block_size
        self._buckets: list[_Item | None] = [None] * initial_block_size
        assert 0.0 < capacity_factor < 1.0
        self._capacity_factor = capacity_factor
        self._len = 0

    def _get_bucket_index(self, key: KEY) -> int:
        return hash(key) % len(self._buckets)

    def _get_next_ind(self, ind: int) -> int:
        """
        Get next index.

        Implements linear open addressing.
        >>> HashMap(5)._get_next_ind(3)
        4
        >>> HashMap(5)._get_next_ind(5)
        1
        >>> HashMap(5)._get_next_ind(6)
        2
        >>> HashMap(5)._get_next_ind(9)
        0
        """
        return (ind + 1) % len(self._buckets)

    def _try_set(self, ind: int, key: KEY, val: VAL) -> bool:
        """
        Try to add value to the bucket.

        If bucket is empty or key is the same, does insert and return True.

        If bucket has another key that means that we need to check next bucket.
        """
        stored = self._buckets[ind]
        if not stored:
            # A falsy item means that bucket was never used (None)
            # or was deleted (_deleted).
            self._buckets[ind] = _Item(key, val)
            self._len += 1
            return True
        elif stored.key == key:
            stored.val = val
            return True
        else:
            return False

    def _is_full(self) -> bool:
        """
        Return true if we have reached safe capacity.

        So we need to increase the number of buckets to avoid collisions.

        >>> hm = HashMap(2)
        >>> hm._add_item(1, 10)
        >>> hm._add_item(2, 20)
        >>> hm._is_full()
        True
        >>> HashMap(2)._is_full()
        False
        """
        limit = len(self._buckets) * self._capacity_factor
        return len(self) >= int(limit)

    def _is_sparse(self) -> bool:
        """Return true if we need twice fewer buckets when we have now."""
        if len(self._buckets) <= self._initial_block_size:
            return False
        limit = len(self._buckets) * self._capacity_factor / 2
        return len(self) < limit

    def _resize(self, new_size: int) -> None:
        old_buckets = self._buckets
        self._buckets = [None] * new_size
        self._len = 0
        for item in old_buckets:
            if item:
                self._add_item(item.key, item.val)

    def _size_up(self) -> None:
        self._resize(len(self._buckets) * 2)

    def _size_down(self) -> None:
        self._resize(len(self._buckets) // 2)

    def _iterate_buckets(self, key: KEY) -> Iterator[int]:
        ind = self._get_bucket_index(key)
        for _ in range(len(self._buckets)):
            yield ind
            ind = self._get_next_ind(ind)

    def _add_item(self, key: KEY, val: VAL) -> None:
        """
        Try to add 3 elements when the size is 5
        >>> hm = HashMap(5)
        >>> hm._add_item(1, 10)
        >>> hm._add_item(2, 20)
        >>> hm._add_item(3, 30)
        >>> hm
        HashMap(1: 10, 2: 20, 3: 30)

        Try to add 3 elements when the size is 5
        >>> hm = HashMap(5)
        >>> hm._add_item(-5, 10)
        >>> hm._add_item(6, 30)
        >>> hm._add_item(-7, 20)
        >>> hm
        HashMap(-5: 10, 6: 30, -7: 20)

        Try to add 3 elements when size is 1
        >>> hm = HashMap(1)
        >>> hm._add_item(10, 13.2)
        >>> hm._add_item(6, 5.26)
        >>> hm._add_item(7, 5.155)
        >>> hm
        HashMap(10: 13.2)

        Trying to add an element with a key that is a floating point value
        >>> hm = HashMap(5)
        >>> hm._add_item(1.5, 10)
        >>> hm
        HashMap(1.5: 10)

        5. Trying to add an item with the same key
        >>> hm = HashMap(5)
        >>> hm._add_item(1, 10)
        >>> hm._add_item(1, 20)
        >>> hm
        HashMap(1: 20)
        """
        for ind in self._iterate_buckets(key):
            if self._try_set(ind, key, val):
                break

    def __setitem__(self, key: KEY, val: VAL) -> None:
        """
        1. Changing value of item whose key is present
        >>> hm = HashMap(5)
        >>> hm._add_item(1, 10)
        >>> hm.__setitem__(1, 20)
        >>> hm
        HashMap(1: 20)

        2. Changing value of item whose key is not present
        >>> hm = HashMap(5)
        >>> hm._add_item(1, 10)
        >>> hm.__setitem__(0, 20)
        >>> hm
        HashMap(0: 20, 1: 10)

        3. Changing the value of the same item multiple times
        >>> hm = HashMap(5)
        >>> hm._add_item(1, 10)
        >>> hm.__setitem__(1, 20)
        >>> hm.__setitem__(1, 30)
        >>> hm
        HashMap(1: 30)
        """
        if self._is_full():
            self._size_up()

        self._add_item(key, val)

    def __delitem__(self, key: KEY) -> None:
        """
        >>> hm = HashMap(5)
        >>> hm._add_item(1, 10)
        >>> hm._add_item(2, 20)
        >>> hm._add_item(3, 30)
        >>> hm.__delitem__(3)
        >>> hm
        HashMap(1: 10, 2: 20)
        >>> hm = HashMap(5)
        >>> hm._add_item(-5, 10)
        >>> hm._add_item(6, 30)
        >>> hm._add_item(-7, 20)
        >>> hm.__delitem__(-5)
        >>> hm
        HashMap(6: 30, -7: 20)

        # Trying to remove a non-existing item
        >>> hm = HashMap(5)
        >>> hm._add_item(1, 10)
        >>> hm._add_item(2, 20)
        >>> hm._add_item(3, 30)
        >>> hm.__delitem__(4)
        Traceback (most recent call last):
        ...
        KeyError: 4

        # Test resize down when sparse
        ## Setup: resize up
        >>> hm = HashMap(initial_block_size=100, capacity_factor=0.75)
        >>> len(hm._buckets)
        100
        >>> for i in range(75):
        ...     hm[i] = i
        >>> len(hm._buckets)
        100
        >>> hm[75] = 75
        >>> len(hm._buckets)
        200

        ## Resize down
        >>> del hm[75]
        >>> len(hm._buckets)
        200
        >>> del hm[74]
        >>> len(hm._buckets)
        100
        """
        for ind in self._iterate_buckets(key):
            item = self._buckets[ind]
            if item is None:
                raise KeyError(key)
            if item is _deleted:
                continue
            if item.key == key:
                self._buckets[ind] = _deleted
                self._len -= 1
                break
        if self._is_sparse():
            self._size_down()

    def __getitem__(self, key: KEY) -> VAL:
        """
        Returns the item at the given key

        >>> hm = HashMap(5)
        >>> hm._add_item(1, 10)
        >>> hm.__getitem__(1)
        10

        >>> hm = HashMap(5)
        >>> hm._add_item(10, -10)
        >>> hm._add_item(20, -20)
        >>> hm.__getitem__(20)
        -20

        >>> hm = HashMap(5)
        >>> hm._add_item(-1, 10)
        >>> hm.__getitem__(-1)
        10
        """
        for ind in self._iterate_buckets(key):
            item = self._buckets[ind]
            if item is None:
                break
            if item is _deleted:
                continue
            if item.key == key:
                return item.val
        raise KeyError(key)

    def __len__(self) -> int:
        """
        Returns the number of items present in hashmap

        >>> hm = HashMap(5)
        >>> hm._add_item(1, 10)
        >>> hm._add_item(2, 20)
        >>> hm._add_item(3, 30)
        >>> hm.__len__()
        3

        >>> hm = HashMap(5)
        >>> hm.__len__()
        0
        """
        return self._len

    def __iter__(self) -> Iterator[KEY]:
        yield from (item.key for item in self._buckets if item)

    def __repr__(self) -> str:
        val_string = ", ".join(
            f"{item.key}: {item.val}" for item in self._buckets if item
        )
        return f"HashMap({val_string})"


if __name__ == "__main__":
    import doctest

    doctest.testmod()

======================

from collections import deque

from .hash_table import HashTable


class HashTableWithLinkedList(HashTable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _set_value(self, key, data):
        self.values[key] = deque([]) if self.values[key] is None else self.values[key]
        self.values[key].appendleft(data)
        self._keys[key] = self.values[key]

    def balanced_factor(self):
        return (
            sum(self.charge_factor - len(slot) for slot in self.values)
            / self.size_table
            * self.charge_factor
        )

    def _collision_resolution(self, key, data=None):
        if not (
            len(self.values[key]) == self.charge_factor and self.values.count(None) == 0
        ):
            return key
        return super()._collision_resolution(key, data)

=======================================


