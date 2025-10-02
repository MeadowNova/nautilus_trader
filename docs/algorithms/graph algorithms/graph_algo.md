"""
pseudo-code

DIJKSTRA(graph G, start vertex s, destination vertex d):

//all nodes initially unexplored

1 -  let H = min heap data structure, initialized with 0 and s [here 0 indicates
     the distance from start vertex s]
2 -  while H is non-empty:
3 -    remove the first node and cost of H, call it U and cost
4 -    if U has been previously explored:
5 -      go to the while loop, line 2 //Once a node is explored there is no need
         to make it again
6 -    mark U as explored
7 -    if U is d:
8 -      return cost // total cost from start to destination vertex
9 -    for each edge(U, V): c=cost of edge(U,V) // for V in graph[U]
10 -     if V explored:
11 -       go to next V in line 9
12 -     total_cost = cost + c
13 -     add (total_cost,V) to H

You can think at cost as a distance where Dijkstra finds the shortest distance
between vertices s and v in a graph G. The use of a min heap as H guarantees
that if a vertex has already been explored there will be no other path with
shortest distance, that happens because heapq.heappop will always return the
next vertex with the shortest distance, considering that the heap stores not
only the distance between previous vertex and current vertex but the entire
distance between each vertex that makes up the path from start vertex to target
vertex.
"""

import heapq


def dijkstra(graph, start, end):
    """Return the cost of the shortest path between vertices start and end.

    >>> dijkstra(G, "E", "C")
    6
    >>> dijkstra(G2, "E", "F")
    3
    >>> dijkstra(G3, "E", "F")
    3
    """

    heap = [(0, start)]  # cost from start node,end node
    visited = set()
    while heap:
        (cost, u) = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        if u == end:
            return cost
        for v, c in graph[u]:
            if v in visited:
                continue
            next_item = cost + c
            heapq.heappush(heap, (next_item, v))
    return -1


G = {
    "A": [["B", 2], ["C", 5]],
    "B": [["A", 2], ["D", 3], ["E", 1], ["F", 1]],
    "C": [["A", 5], ["F", 3]],
    "D": [["B", 3]],
    "E": [["B", 4], ["F", 3]],
    "F": [["C", 3], ["E", 3]],
}

r"""
Layout of G2:

E -- 1 --> B -- 1 --> C -- 1 --> D -- 1 --> F
 \                                         /\
  \                                        ||
    ----------------- 3 --------------------
"""
G2 = {
    "B": [["C", 1]],
    "C": [["D", 1]],
    "D": [["F", 1]],
    "E": [["B", 1], ["F", 3]],
    "F": [],
}

r"""
Layout of G3:

E -- 1 --> B -- 1 --> C -- 1 --> D -- 1 --> F
 \                                         /\
  \                                        ||
    -------- 2 ---------> G ------- 1 ------
"""
G3 = {
    "B": [["C", 1]],
    "C": [["D", 1]],
    "D": [["F", 1]],
    "E": [["B", 1], ["G", 2]],
    "F": [],
    "G": [["F", 1]],
}

short_distance = dijkstra(G, "E", "C")
print(short_distance)  # E -- 3 --> F -- 3 --> C == 6

short_distance = dijkstra(G2, "E", "F")
print(short_distance)  # E -- 3 --> F == 3

short_distance = dijkstra(G3, "E", "F")
print(short_distance)  # E -- 2 --> G -- 1 --> F == 3

if __name__ == "__main__":
    import doctest

    doctest.testmod()

====================================

from __future__ import annotations


def print_distance(distance: list[float], src):
    print(f"Vertex\tShortest Distance from vertex {src}")
    for i, d in enumerate(distance):
        print(f"{i}\t\t{d}")


def check_negative_cycle(
    graph: list[dict[str, int]], distance: list[float], edge_count: int
):
    for j in range(edge_count):
        u, v, w = (graph[j][k] for k in ["src", "dst", "weight"])
        if distance[u] != float("inf") and distance[u] + w < distance[v]:
            return True
    return False


def bellman_ford(
    graph: list[dict[str, int]], vertex_count: int, edge_count: int, src: int
) -> list[float]:
    """
    Returns shortest paths from a vertex src to all
    other vertices.
    >>> edges = [(2, 1, -10), (3, 2, 3), (0, 3, 5), (0, 1, 4)]
    >>> g = [{"src": s, "dst": d, "weight": w} for s, d, w in edges]
    >>> bellman_ford(g, 4, 4, 0)
    [0.0, -2.0, 8.0, 5.0]
    >>> g = [{"src": s, "dst": d, "weight": w} for s, d, w in edges + [(1, 3, 5)]]
    >>> bellman_ford(g, 4, 5, 0)
    Traceback (most recent call last):
     ...
    Exception: Negative cycle found
    """
    distance = [float("inf")] * vertex_count
    distance[src] = 0.0

    for _ in range(vertex_count - 1):
        for j in range(edge_count):
            u, v, w = (graph[j][k] for k in ["src", "dst", "weight"])

            if distance[u] != float("inf") and distance[u] + w < distance[v]:
                distance[v] = distance[u] + w

    negative_cycle_exists = check_negative_cycle(graph, distance, edge_count)
    if negative_cycle_exists:
        raise Exception("Negative cycle found")

    return distance


if __name__ == "__main__":
    import doctest

    doctest.testmod()

    V = int(input("Enter number of vertices: ").strip())
    E = int(input("Enter number of edges: ").strip())

    graph: list[dict[str, int]] = [{} for _ in range(E)]

    for i in range(E):
        print("Edge ", i + 1)
        src, dest, weight = (
            int(x)
            for x in input("Enter source, destination, weight: ").strip().split(" ")
        )
        graph[i] = {"src": src, "dst": dest, "weight": weight}

    source = int(input("\nEnter shortest path source:").strip())
    shortest_distance = bellman_ford(graph, V, E, source)
    print_distance(shortest_distance, 0)

=======================================

# floyd_warshall.py
"""
The problem is to find the shortest distance between all pairs of vertices in a
weighted directed graph that can have negative edge weights.
"""


def _print_dist(dist, v):
    print("\nThe shortest path matrix using Floyd Warshall algorithm\n")
    for i in range(v):
        for j in range(v):
            if dist[i][j] != float("inf"):
                print(int(dist[i][j]), end="\t")
            else:
                print("INF", end="\t")
        print()


def floyd_warshall(graph, v):
    """
    :param graph: 2D array calculated from weight[edge[i, j]]
    :type graph: List[List[float]]
    :param v: number of vertices
    :type v: int
    :return: shortest distance between all vertex pairs
    distance[u][v] will contain the shortest distance from vertex u to v.

    1. For all edges from v to n, distance[i][j] = weight(edge(i, j)).
    3. The algorithm then performs distance[i][j] = min(distance[i][j], distance[i][k] +
        distance[k][j]) for each possible pair i, j of vertices.
    4. The above is repeated for each vertex k in the graph.
    5. Whenever distance[i][j] is given a new minimum value, next vertex[i][j] is
        updated to the next vertex[i][k].
    """

    dist = [[float("inf") for _ in range(v)] for _ in range(v)]

    for i in range(v):
        for j in range(v):
            dist[i][j] = graph[i][j]

            # check vertex k against all other vertices (i, j)
    for k in range(v):
        # looping through rows of graph array
        for i in range(v):
            # looping through columns of graph array
            for j in range(v):
                if (
                    dist[i][k] != float("inf")
                    and dist[k][j] != float("inf")
                    and dist[i][k] + dist[k][j] < dist[i][j]
                ):
                    dist[i][j] = dist[i][k] + dist[k][j]

    _print_dist(dist, v)
    return dist, v


if __name__ == "__main__":
    v = int(input("Enter number of vertices: "))
    e = int(input("Enter number of edges: "))

    graph = [[float("inf") for i in range(v)] for j in range(v)]

    for i in range(v):
        graph[i][i] = 0.0

        # src and dst are indices that must be within the array size graph[e][v]
        # failure to follow this will result in an error
    for i in range(e):
        print("\nEdge ", i + 1)
        src = int(input("Enter source:"))
        dst = int(input("Enter destination:"))
        weight = float(input("Enter weight:"))
        graph[src][dst] = weight

    floyd_warshall(graph, v)

    # Example Input
    # Enter number of vertices: 3
    # Enter number of edges: 2

    # # generated graph from vertex and edge inputs
    # [[inf, inf, inf], [inf, inf, inf], [inf, inf, inf]]
    # [[0.0, inf, inf], [inf, 0.0, inf], [inf, inf, 0.0]]

    # specify source, destination and weight for edge #1
    # Edge  1
    # Enter source:1
    # Enter destination:2
    # Enter weight:2

    # specify source, destination and weight for edge #2
    # Edge  2
    # Enter source:2
    # Enter destination:1
    # Enter weight:1

    # # Expected Output from the vertice, edge and src, dst, weight inputs!!
    # 0		INF	INF
    # INF	0	2
    # INF	1	0

======================================

class Graph:
    """
    Data structure to store graphs (based on adjacency lists)
    """

    def __init__(self):
        self.num_vertices = 0
        self.num_edges = 0
        self.adjacency = {}

    def add_vertex(self, vertex):
        """
        Adds a vertex to the graph

        """
        if vertex not in self.adjacency:
            self.adjacency[vertex] = {}
            self.num_vertices += 1

    def add_edge(self, head, tail, weight):
        """
        Adds an edge to the graph

        """

        self.add_vertex(head)
        self.add_vertex(tail)

        if head == tail:
            return

        self.adjacency[head][tail] = weight
        self.adjacency[tail][head] = weight

    def distinct_weight(self):
        """
        For Boruvks's algorithm the weights should be distinct
        Converts the weights to be distinct

        """
        edges = self.get_edges()
        for edge in edges:
            head, tail, weight = edge
            edges.remove((tail, head, weight))
        for i in range(len(edges)):
            edges[i] = list(edges[i])

        edges.sort(key=lambda e: e[2])
        for i in range(len(edges) - 1):
            if edges[i][2] >= edges[i + 1][2]:
                edges[i + 1][2] = edges[i][2] + 1
        for edge in edges:
            head, tail, weight = edge
            self.adjacency[head][tail] = weight
            self.adjacency[tail][head] = weight

    def __str__(self):
        """
        Returns string representation of the graph
        """
        string = ""
        for tail in self.adjacency:
            for head in self.adjacency[tail]:
                weight = self.adjacency[head][tail]
                string += f"{head} -> {tail} == {weight}\n"
        return string.rstrip("\n")

    def get_edges(self):
        """
        Returna all edges in the graph
        """
        output = []
        for tail in self.adjacency:
            for head in self.adjacency[tail]:
                output.append((tail, head, self.adjacency[head][tail]))
        return output

    def get_vertices(self):
        """
        Returns all vertices in the graph
        """
        return self.adjacency.keys()

    @staticmethod
    def build(vertices=None, edges=None):
        """
        Builds a graph from the given set of vertices and edges

        """
        g = Graph()
        if vertices is None:
            vertices = []
        if edges is None:
            edge = []
        for vertex in vertices:
            g.add_vertex(vertex)
        for edge in edges:
            g.add_edge(*edge)
        return g

    class UnionFind:
        """
        Disjoint set Union and Find for Boruvka's algorithm
        """

        def __init__(self):
            self.parent = {}
            self.rank = {}

        def __len__(self):
            return len(self.parent)

        def make_set(self, item):
            if item in self.parent:
                return self.find(item)

            self.parent[item] = item
            self.rank[item] = 0
            return item

        def find(self, item):
            if item not in self.parent:
                return self.make_set(item)
            if item != self.parent[item]:
                self.parent[item] = self.find(self.parent[item])
            return self.parent[item]

        def union(self, item1, item2):
            root1 = self.find(item1)
            root2 = self.find(item2)

            if root1 == root2:
                return root1

            if self.rank[root1] > self.rank[root2]:
                self.parent[root2] = root1
                return root1

            if self.rank[root1] < self.rank[root2]:
                self.parent[root1] = root2
                return root2

            if self.rank[root1] == self.rank[root2]:
                self.rank[root1] += 1
                self.parent[root2] = root1
                return root1
            return None

    @staticmethod
    def boruvka_mst(graph):
        """
        Implementation of Boruvka's algorithm
        >>> g = Graph()
        >>> g = Graph.build([0, 1, 2, 3], [[0, 1, 1], [0, 2, 1],[2, 3, 1]])
        >>> g.distinct_weight()
        >>> bg = Graph.boruvka_mst(g)
        >>> print(bg)
        1 -> 0 == 1
        2 -> 0 == 2
        0 -> 1 == 1
        0 -> 2 == 2
        3 -> 2 == 3
        2 -> 3 == 3
        """
        num_components = graph.num_vertices

        union_find = Graph.UnionFind()
        mst_edges = []
        while num_components > 1:
            cheap_edge = {}
            for vertex in graph.get_vertices():
                cheap_edge[vertex] = -1

            edges = graph.get_edges()
            for edge in edges:
                head, tail, weight = edge
                edges.remove((tail, head, weight))
            for edge in edges:
                head, tail, weight = edge
                set1 = union_find.find(head)
                set2 = union_find.find(tail)
                if set1 != set2:
                    if cheap_edge[set1] == -1 or cheap_edge[set1][2] > weight:
                        cheap_edge[set1] = [head, tail, weight]

                    if cheap_edge[set2] == -1 or cheap_edge[set2][2] > weight:
                        cheap_edge[set2] = [head, tail, weight]
            for head_tail_weight in cheap_edge.values():
                if head_tail_weight != -1:
                    head, tail, weight = head_tail_weight
                    if union_find.find(head) != union_find.find(tail):
                        union_find.union(head, tail)
                        mst_edges.append(head_tail_weight)
                        num_components = num_components - 1
        mst = Graph.build(edges=mst_edges)
        return mst

=========================================

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


class DisjointSetTreeNode[T]:
    # Disjoint Set Node to store the parent and rank
    def __init__(self, data: T) -> None:
        self.data = data
        self.parent = self
        self.rank = 0


class DisjointSetTree[T]:
    # Disjoint Set DataStructure
    def __init__(self) -> None:
        # map from node name to the node object
        self.map: dict[T, DisjointSetTreeNode[T]] = {}

    def make_set(self, data: T) -> None:
        # create a new set with x as its member
        self.map[data] = DisjointSetTreeNode(data)

    def find_set(self, data: T) -> DisjointSetTreeNode[T]:
        # find the set x belongs to (with path-compression)
        elem_ref = self.map[data]
        if elem_ref != elem_ref.parent:
            elem_ref.parent = self.find_set(elem_ref.parent.data)
        return elem_ref.parent

    def link(
        self, node1: DisjointSetTreeNode[T], node2: DisjointSetTreeNode[T]
    ) -> None:
        # helper function for union operation
        if node1.rank > node2.rank:
            node2.parent = node1
        else:
            node1.parent = node2
            if node1.rank == node2.rank:
                node2.rank += 1

    def union(self, data1: T, data2: T) -> None:
        # merge 2 disjoint sets
        self.link(self.find_set(data1), self.find_set(data2))


class GraphUndirectedWeighted[T]:
    def __init__(self) -> None:
        # connections: map from the node to the neighbouring nodes (with weights)
        self.connections: dict[T, dict[T, int]] = {}

    def add_node(self, node: T) -> None:
        # add a node ONLY if its not present in the graph
        if node not in self.connections:
            self.connections[node] = {}

    def add_edge(self, node1: T, node2: T, weight: int) -> None:
        # add an edge with the given weight
        self.add_node(node1)
        self.add_node(node2)
        self.connections[node1][node2] = weight
        self.connections[node2][node1] = weight

    def kruskal(self) -> GraphUndirectedWeighted[T]:
        # Kruskal's Algorithm to generate a Minimum Spanning Tree (MST) of a graph
        """
        Details: https://en.wikipedia.org/wiki/Kruskal%27s_algorithm

        Example:
        >>> g1 = GraphUndirectedWeighted[int]()
        >>> g1.add_edge(1, 2, 1)
        >>> g1.add_edge(2, 3, 2)
        >>> g1.add_edge(3, 4, 1)
        >>> g1.add_edge(3, 5, 100) # Removed in MST
        >>> g1.add_edge(4, 5, 5)
        >>> assert 5 in g1.connections[3]
        >>> mst = g1.kruskal()
        >>> assert 5 not in mst.connections[3]

        >>> g2 = GraphUndirectedWeighted[str]()
        >>> g2.add_edge('A', 'B', 1)
        >>> g2.add_edge('B', 'C', 2)
        >>> g2.add_edge('C', 'D', 1)
        >>> g2.add_edge('C', 'E', 100) # Removed in MST
        >>> g2.add_edge('D', 'E', 5)
        >>> assert 'E' in g2.connections["C"]
        >>> mst = g2.kruskal()
        >>> assert 'E' not in mst.connections['C']
        """

        # getting the edges in ascending order of weights
        edges = []
        seen = set()
        for start in self.connections:
            for end in self.connections[start]:
                if (start, end) not in seen:
                    seen.add((end, start))
                    edges.append((start, end, self.connections[start][end]))
        edges.sort(key=lambda x: x[2])

        # creating the disjoint set
        disjoint_set = DisjointSetTree[T]()
        for node in self.connections:
            disjoint_set.make_set(node)

        # MST generation
        num_edges = 0
        index = 0
        graph = GraphUndirectedWeighted[T]()
        while num_edges < len(self.connections) - 1:
            u, v, w = edges[index]
            index += 1
            parent_u = disjoint_set.find_set(u)
            parent_v = disjoint_set.find_set(v)
            if parent_u != parent_v:
                num_edges += 1
                graph.add_edge(u, v, w)
                disjoint_set.union(u, v)
        return graph

==================================================

"""
Author: https://github.com/bhushan-borole
"""

"""
The input graph for the algorithm is:

  A B C
A 0 1 1
B 0 0 1
C 1 0 0

"""

graph = [[0, 1, 1], [0, 0, 1], [1, 0, 0]]


class Node:
    def __init__(self, name):
        self.name = name
        self.inbound = []
        self.outbound = []

    def add_inbound(self, node):
        self.inbound.append(node)

    def add_outbound(self, node):
        self.outbound.append(node)

    def __repr__(self):
        return f"<node={self.name} inbound={self.inbound} outbound={self.outbound}>"


def page_rank(nodes, limit=3, d=0.85):
    ranks = {}
    for node in nodes:
        ranks[node.name] = 1

    outbounds = {}
    for node in nodes:
        outbounds[node.name] = len(node.outbound)

    for i in range(limit):
        print(f"======= Iteration {i + 1} =======")
        for _, node in enumerate(nodes):
            ranks[node.name] = (1 - d) + d * sum(
                ranks[ib] / outbounds[ib] for ib in node.inbound
            )
        print(ranks)


def main():
    names = list(input("Enter Names of the Nodes: ").split())

    nodes = [Node(name) for name in names]

    for ri, row in enumerate(graph):
        for ci, col in enumerate(row):
            if col == 1:
                nodes[ci].add_inbound(names[ri])
                nodes[ri].add_outbound(names[ci])

    print("======= Nodes =======")
    for node in nodes:
        print(node)

    page_rank(nodes)


if __name__ == "__main__":
    main()

===========================================

from __future__ import annotations

from collections import Counter
from random import random


class MarkovChainGraphUndirectedUnweighted:
    """
    Undirected Unweighted Graph for running Markov Chain Algorithm
    """

    def __init__(self):
        self.connections = {}

    def add_node(self, node: str) -> None:
        self.connections[node] = {}

    def add_transition_probability(
        self, node1: str, node2: str, probability: float
    ) -> None:
        if node1 not in self.connections:
            self.add_node(node1)
        if node2 not in self.connections:
            self.add_node(node2)
        self.connections[node1][node2] = probability

    def get_nodes(self) -> list[str]:
        return list(self.connections)

    def transition(self, node: str) -> str:
        current_probability = 0
        random_value = random()

        for dest in self.connections[node]:
            current_probability += self.connections[node][dest]
            if current_probability > random_value:
                return dest
        return ""


def get_transitions(
    start: str, transitions: list[tuple[str, str, float]], steps: int
) -> dict[str, int]:
    """
    Running Markov Chain algorithm and calculating the number of times each node is
    visited

    >>> transitions = [
    ... ('a', 'a', 0.9),
    ... ('a', 'b', 0.075),
    ... ('a', 'c', 0.025),
    ... ('b', 'a', 0.15),
    ... ('b', 'b', 0.8),
    ... ('b', 'c', 0.05),
    ... ('c', 'a', 0.25),
    ... ('c', 'b', 0.25),
    ... ('c', 'c', 0.5)
    ... ]

    >>> result = get_transitions('a', transitions, 5000)

    >>> result['a'] > result['b'] > result['c']
    True
    """

    graph = MarkovChainGraphUndirectedUnweighted()

    for node1, node2, probability in transitions:
        graph.add_transition_probability(node1, node2, probability)

    visited = Counter(graph.get_nodes())
    node = start

    for _ in range(steps):
        node = graph.transition(node)
        visited[node] += 1

    return visited


if __name__ == "__main__":
    import doctest

    doctest.testmod()

