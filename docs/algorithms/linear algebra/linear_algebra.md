"""
Resources:
- https://en.wikipedia.org/wiki/Conjugate_gradient_method
- https://en.wikipedia.org/wiki/Definite_symmetric_matrix
"""

from typing import Any

import numpy as np


def _is_matrix_spd(matrix: np.ndarray) -> bool:
    """
    Returns True if input matrix is symmetric positive definite.
    Returns False otherwise.

    For a matrix to be SPD, all eigenvalues must be positive.

    >>> import numpy as np
    >>> matrix = np.array([
    ... [4.12401784, -5.01453636, -0.63865857],
    ... [-5.01453636, 12.33347422, -3.40493586],
    ... [-0.63865857, -3.40493586,  5.78591885]])
    >>> _is_matrix_spd(matrix)
    True
    >>> matrix = np.array([
    ... [0.34634879,  1.96165514,  2.18277744],
    ... [0.74074469, -1.19648894, -1.34223498],
    ... [-0.7687067 ,  0.06018373, -1.16315631]])
    >>> _is_matrix_spd(matrix)
    False
    """
    # Ensure matrix is square.
    assert np.shape(matrix)[0] == np.shape(matrix)[1]

    # If matrix not symmetric, exit right away.
    if np.allclose(matrix, matrix.T) is False:
        return False

    # Get eigenvalues and eignevectors for a symmetric matrix.
    eigen_values, _ = np.linalg.eigh(matrix)

    # Check sign of all eigenvalues.
    # np.all returns a value of type np.bool_
    return bool(np.all(eigen_values > 0))


def _create_spd_matrix(dimension: int) -> Any:
    """
    Returns a symmetric positive definite matrix given a dimension.

    Input:
    dimension gives the square matrix dimension.

    Output:
    spd_matrix is an diminesion x dimensions symmetric positive definite (SPD) matrix.

    >>> import numpy as np
    >>> dimension = 3
    >>> spd_matrix = _create_spd_matrix(dimension)
    >>> _is_matrix_spd(spd_matrix)
    True
    """
    rng = np.random.default_rng()
    random_matrix = rng.normal(size=(dimension, dimension))
    spd_matrix = np.dot(random_matrix, random_matrix.T)
    assert _is_matrix_spd(spd_matrix)
    return spd_matrix


def conjugate_gradient(
    spd_matrix: np.ndarray,
    load_vector: np.ndarray,
    max_iterations: int = 1000,
    tol: float = 1e-8,
) -> Any:
    """
    Returns solution to the linear system np.dot(spd_matrix, x) = b.

    Input:
    spd_matrix is an NxN Symmetric Positive Definite (SPD) matrix.
    load_vector is an Nx1 vector.

    Output:
    x is an Nx1 vector that is the solution vector.

    >>> import numpy as np
    >>> spd_matrix = np.array([
    ... [8.73256573, -5.02034289, -2.68709226],
    ... [-5.02034289,  3.78188322,  0.91980451],
    ... [-2.68709226,  0.91980451,  1.94746467]])
    >>> b = np.array([
    ... [-5.80872761],
    ... [ 3.23807431],
    ... [ 1.95381422]])
    >>> conjugate_gradient(spd_matrix, b)
    array([[-0.63114139],
           [-0.01561498],
           [ 0.13979294]])
    """
    # Ensure proper dimensionality.
    assert np.shape(spd_matrix)[0] == np.shape(spd_matrix)[1]
    assert np.shape(load_vector)[0] == np.shape(spd_matrix)[0]
    assert _is_matrix_spd(spd_matrix)

    # Initialize solution guess, residual, search direction.
    x0 = np.zeros((np.shape(load_vector)[0], 1))
    r0 = np.copy(load_vector)
    p0 = np.copy(r0)

    # Set initial errors in solution guess and residual.
    error_residual = 1e9
    error_x_solution = 1e9
    error = 1e9

    # Set iteration counter to threshold number of iterations.
    iterations = 0

    while error > tol:
        # Save this value so we only calculate the matrix-vector product once.
        w = np.dot(spd_matrix, p0)

        # The main algorithm.

        # Update search direction magnitude.
        alpha = np.dot(r0.T, r0) / np.dot(p0.T, w)
        # Update solution guess.
        x = x0 + alpha * p0
        # Calculate new residual.
        r = r0 - alpha * w
        # Calculate new Krylov subspace scale.
        beta = np.dot(r.T, r) / np.dot(r0.T, r0)
        # Calculate new A conjuage search direction.
        p = r + beta * p0

        # Calculate errors.
        error_residual = np.linalg.norm(r - r0)
        error_x_solution = np.linalg.norm(x - x0)
        error = np.maximum(error_residual, error_x_solution)

        # Update variables.
        x0 = np.copy(x)
        r0 = np.copy(r)
        p0 = np.copy(p)

        # Update number of iterations.
        iterations += 1
        if iterations > max_iterations:
            break

    return x


def test_conjugate_gradient() -> None:
    """
    >>> test_conjugate_gradient()  # self running tests
    """
    # Create linear system with SPD matrix and known solution x_true.
    dimension = 3
    spd_matrix = _create_spd_matrix(dimension)
    rng = np.random.default_rng()
    x_true = rng.normal(size=(dimension, 1))
    b = np.dot(spd_matrix, x_true)

    # Numpy solution.
    x_numpy = np.linalg.solve(spd_matrix, b)

    # Our implementation.
    x_conjugate_gradient = conjugate_gradient(spd_matrix, b)

    # Ensure both solutions are close to x_true (and therefore one another).
    assert np.linalg.norm(x_numpy - x_true) <= 1e-6
    assert np.linalg.norm(x_conjugate_gradient - x_true) <= 1e-6


if __name__ == "__main__":
    import doctest

    doctest.testmod()
    test_conjugate_gradient()

=============================

import numpy as np


def power_iteration(
    input_matrix: np.ndarray,
    vector: np.ndarray,
    error_tol: float = 1e-12,
    max_iterations: int = 100,
) -> tuple[float, np.ndarray]:
    """
    Power Iteration.
    Find the largest eigenvalue and corresponding eigenvector
    of matrix input_matrix given a random vector in the same space.
    Will work so long as vector has component of largest eigenvector.
    input_matrix must be either real or Hermitian.

    Input
    input_matrix: input matrix whose largest eigenvalue we will find.
    Numpy array. np.shape(input_matrix) == (N,N).
    vector: random initial vector in same space as matrix.
    Numpy array. np.shape(vector) == (N,) or (N,1)

    Output
    largest_eigenvalue: largest eigenvalue of the matrix input_matrix.
    Float. Scalar.
    largest_eigenvector: eigenvector corresponding to largest_eigenvalue.
    Numpy array. np.shape(largest_eigenvector) == (N,) or (N,1).

    >>> import numpy as np
    >>> input_matrix = np.array([
    ... [41,  4, 20],
    ... [ 4, 26, 30],
    ... [20, 30, 50]
    ... ])
    >>> vector = np.array([41,4,20])
    >>> power_iteration(input_matrix,vector)
    (79.66086378788381, array([0.44472726, 0.46209842, 0.76725662]))
    """

    # Ensure matrix is square.
    assert np.shape(input_matrix)[0] == np.shape(input_matrix)[1]
    # Ensure proper dimensionality.
    assert np.shape(input_matrix)[0] == np.shape(vector)[0]
    # Ensure inputs are either both complex or both real
    assert np.iscomplexobj(input_matrix) == np.iscomplexobj(vector)
    is_complex = np.iscomplexobj(input_matrix)
    if is_complex:
        # Ensure complex input_matrix is Hermitian
        assert np.array_equal(input_matrix, input_matrix.conj().T)

    # Set convergence to False. Will define convergence when we exceed max_iterations
    # or when we have small changes from one iteration to next.

    convergence = False
    lambda_previous = 0
    iterations = 0
    error = 1e12

    while not convergence:
        # Multiple matrix by the vector.
        w = np.dot(input_matrix, vector)
        # Normalize the resulting output vector.
        vector = w / np.linalg.norm(w)
        # Find rayleigh quotient
        # (faster than usual b/c we know vector is normalized already)
        vector_h = vector.conj().T if is_complex else vector.T
        lambda_ = np.dot(vector_h, np.dot(input_matrix, vector))

        # Check convergence.
        error = np.abs(lambda_ - lambda_previous) / lambda_
        iterations += 1

        if error <= error_tol or iterations >= max_iterations:
            convergence = True

        lambda_previous = lambda_

    if is_complex:
        lambda_ = np.real(lambda_)

    return float(lambda_), vector


def test_power_iteration() -> None:
    """
    >>> test_power_iteration()  # self running tests
    """
    real_input_matrix = np.array([[41, 4, 20], [4, 26, 30], [20, 30, 50]])
    real_vector = np.array([41, 4, 20])
    complex_input_matrix = real_input_matrix.astype(np.complex128)
    imag_matrix = np.triu(1j * complex_input_matrix, 1)
    complex_input_matrix += imag_matrix
    complex_input_matrix += -1 * imag_matrix.T
    complex_vector = np.array([41, 4, 20]).astype(np.complex128)

    for problem_type in ["real", "complex"]:
        if problem_type == "real":
            input_matrix = real_input_matrix
            vector = real_vector
        elif problem_type == "complex":
            input_matrix = complex_input_matrix
            vector = complex_vector

        # Our implementation.
        eigen_value, eigen_vector = power_iteration(input_matrix, vector)

        # Numpy implementation.

        # Get eigenvalues and eigenvectors using built-in numpy
        # eigh (eigh used for symmetric or hermetian matrices).
        eigen_values, eigen_vectors = np.linalg.eigh(input_matrix)
        # Last eigenvalue is the maximum one.
        eigen_value_max = eigen_values[-1]
        # Last column in this matrix is eigenvector corresponding to largest eigenvalue.
        eigen_vector_max = eigen_vectors[:, -1]

        # Check our implementation and numpy gives close answers.
        assert np.abs(eigen_value - eigen_value_max) <= 1e-6
        # Take absolute values element wise of each eigenvector.
        # as they are only unique to a minus sign.
        assert np.linalg.norm(np.abs(eigen_vector) - np.abs(eigen_vector_max)) <= 1e-6


if __name__ == "__main__":
    import doctest

    doctest.testmod()
    test_power_iteration()

==============================

import numpy as np


def solve_linear_system(matrix: np.ndarray) -> np.ndarray:
    """
    Solve a linear system of equations using Gaussian elimination with partial pivoting

    Args:
      - `matrix`: Coefficient matrix with the last column representing the constants.

    Returns:
      - Solution vector.

    Raises:
      - ``ValueError``: If the matrix is not correct (i.e., singular).

    https://courses.engr.illinois.edu/cs357/su2013/lect.htm Lecture 7

    Example:

    >>> A = np.array([[2, 1, -1], [-3, -1, 2], [-2, 1, 2]], dtype=float)
    >>> B = np.array([8, -11, -3], dtype=float)
    >>> solution = solve_linear_system(np.column_stack((A, B)))
    >>> np.allclose(solution, np.array([2., 3., -1.]))
    True
    >>> solve_linear_system(np.array([[0, 0, 0]], dtype=float))
    Traceback (most recent call last):
        ...
    ValueError: Matrix is not square
    >>> solve_linear_system(np.array([[0, 0, 0], [0, 0, 0]], dtype=float))
    Traceback (most recent call last):
        ...
    ValueError: Matrix is singular
    """
    ab = np.copy(matrix)
    num_of_rows = ab.shape[0]
    num_of_columns = ab.shape[1] - 1
    x_lst: list[float] = []

    if num_of_rows != num_of_columns:
        raise ValueError("Matrix is not square")

    for column_num in range(num_of_rows):
        # Lead element search
        for i in range(column_num, num_of_columns):
            if abs(ab[i][column_num]) > abs(ab[column_num][column_num]):
                ab[[column_num, i]] = ab[[i, column_num]]

        # Upper triangular matrix
        if abs(ab[column_num, column_num]) < 1e-8:
            raise ValueError("Matrix is singular")

        if column_num != 0:
            for i in range(column_num, num_of_rows):
                ab[i, :] -= (
                    ab[i, column_num - 1]
                    / ab[column_num - 1, column_num - 1]
                    * ab[column_num - 1, :]
                )

    # Find x vector (Back Substitution)
    for column_num in range(num_of_rows - 1, -1, -1):
        x = ab[column_num, -1] / ab[column_num, column_num]
        x_lst.insert(0, x)
        for i in range(column_num - 1, -1, -1):
            ab[i, -1] -= ab[i, column_num] * x

    # Return the solution vector
    return np.asarray(x_lst)


if __name__ == "__main__":
    from doctest import testmod

    testmod()

    example_matrix = np.array(
        [
            [5.0, -5.0, -3.0, 4.0, -11.0],
            [1.0, -4.0, 6.0, -4.0, -10.0],
            [-2.0, -5.0, 4.0, -5.0, -12.0],
            [-3.0, -3.0, 5.0, -5.0, 8.0],
        ],
        dtype=float,
    )

    print(f"Matrix:\n{example_matrix}")
    print(f"{solve_linear_system(example_matrix) = }")

==========================================

import numpy as np


def invert_matrix(matrix: list[list[float]]) -> list[list[float]]:
    """
    Returns the inverse of a square matrix using NumPy.

    Parameters:
    matrix (list[list[float]]): A square matrix.

    Returns:
    list[list[float]]: Inverted matrix if invertible, else raises error.

    >>> invert_matrix([[4.0, 7.0], [2.0, 6.0]])
    [[0.6000000000000001, -0.7000000000000001], [-0.2, 0.4]]
    >>> invert_matrix([[1.0, 2.0], [0.0, 0.0]])
    Traceback (most recent call last):
        ...
    ValueError: Matrix is not invertible
    """
    np_matrix = np.array(matrix)

    try:
        inv_matrix = np.linalg.inv(np_matrix)
    except np.linalg.LinAlgError:
        raise ValueError("Matrix is not invertible")

    return inv_matrix.tolist()


if __name__ == "__main__":
    mat = [[4.0, 7.0], [2.0, 6.0]]
    print("Original Matrix:")
    print(mat)
    print("Inverted Matrix:")
    print(invert_matrix(mat))

