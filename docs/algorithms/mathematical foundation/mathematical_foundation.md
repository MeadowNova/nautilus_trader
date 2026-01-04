"""
The Newton-Raphson method (aka the Newton method) is a root-finding algorithm that
approximates a root of a given real-valued function f(x). It is an iterative method
given by the formula

x_{n + 1} = x_n + f(x_n) / f'(x_n)

with the precision of the approximation increasing as the number of iterations increase.

Reference: https://en.wikipedia.org/wiki/Newton%27s_method
"""

from collections.abc import Callable

RealFunc = Callable[[float], float]


def calc_derivative(f: RealFunc, x: float, delta_x: float = 1e-3) -> float:
    """
    Approximate the derivative of a function f(x) at a point x using the finite
    difference method

    >>> import math
    >>> tolerance = 1e-5
    >>> derivative = calc_derivative(lambda x: x**2, 2)
    >>> math.isclose(derivative, 4, abs_tol=tolerance)
    True
    >>> derivative = calc_derivative(math.sin, 0)
    >>> math.isclose(derivative, 1, abs_tol=tolerance)
    True
    """
    return (f(x + delta_x / 2) - f(x - delta_x / 2)) / delta_x


def newton_raphson(
    f: RealFunc,
    x0: float = 0,
    max_iter: int = 100,
    step: float = 1e-6,
    max_error: float = 1e-6,
    log_steps: bool = False,
) -> tuple[float, float, list[float]]:
    """
    Find a root of the given function f using the Newton-Raphson method.

    :param f: A real-valued single-variable function
    :param x0: Initial guess
    :param max_iter: Maximum number of iterations
    :param step: Step size of x, used to approximate f'(x)
    :param max_error: Maximum approximation error
    :param log_steps: bool denoting whether to log intermediate steps

    :return: A tuple containing the approximation, the error, and the intermediate
        steps. If log_steps is False, then an empty list is returned for the third
        element of the tuple.

    :raises ZeroDivisionError: The derivative approaches 0.
    :raises ArithmeticError: No solution exists, or the solution isn't found before the
        iteration limit is reached.

    >>> import math
    >>> tolerance = 1e-15
    >>> root, *_ = newton_raphson(lambda x: x**2 - 5*x + 2, 0.4, max_error=tolerance)
    >>> math.isclose(root, (5 - math.sqrt(17)) / 2, abs_tol=tolerance)
    True
    >>> root, *_ = newton_raphson(lambda x: math.log(x) - 1, 2, max_error=tolerance)
    >>> math.isclose(root, math.e, abs_tol=tolerance)
    True
    >>> root, *_ = newton_raphson(math.sin, 1, max_error=tolerance)
    >>> math.isclose(root, 0, abs_tol=tolerance)
    True
    >>> newton_raphson(math.cos, 0)
    Traceback (most recent call last):
    ...
    ZeroDivisionError: No converging solution found, zero derivative
    >>> newton_raphson(lambda x: x**2 + 1, 2)
    Traceback (most recent call last):
    ...
    ArithmeticError: No converging solution found, iteration limit reached
    """

    def f_derivative(x: float) -> float:
        return calc_derivative(f, x, step)

    a = x0  # Set initial guess
    steps = []
    for _ in range(max_iter):
        if log_steps:  # Log intermediate steps
            steps.append(a)

        error = abs(f(a))
        if error < max_error:
            return a, error, steps

        if f_derivative(a) == 0:
            raise ZeroDivisionError("No converging solution found, zero derivative")
        a -= f(a) / f_derivative(a)  # Calculate next estimate
    raise ArithmeticError("No converging solution found, iteration limit reached")


if __name__ == "__main__":
    import doctest
    from math import exp, tanh

    doctest.testmod()

    def func(x: float) -> float:
        return tanh(x) ** 2 - exp(3 * x)

    solution, err, steps = newton_raphson(
        func, x0=10, max_iter=100, step=1e-6, log_steps=True
    )
    print(f"{solution=}, {err=}")
    print("\n".join(str(x) for x in steps))

==========================================

import numpy as np


def runge_kutta(f, y0, x0, h, x_end):
    """
    Calculate the numeric solution at each step to the ODE f(x, y) using RK4

    https://en.wikipedia.org/wiki/Runge-Kutta_methods

    Arguments:
    f -- The ode as a function of x and y
    y0 -- the initial value for y
    x0 -- the initial value for x
    h -- the stepsize
    x_end -- the end value for x

    >>> # the exact solution is math.exp(x)
    >>> def f(x, y):
    ...     return y
    >>> y0 = 1
    >>> y = runge_kutta(f, y0, 0.0, 0.01, 5)
    >>> float(y[-1])
    148.41315904125113
    """
    n = int(np.ceil((x_end - x0) / h))
    y = np.zeros((n + 1,))
    y[0] = y0
    x = x0

    for k in range(n):
        k1 = f(x, y[k])
        k2 = f(x + 0.5 * h, y[k] + 0.5 * h * k1)
        k3 = f(x + 0.5 * h, y[k] + 0.5 * h * k2)
        k4 = f(x + h, y[k] + h * k3)
        y[k + 1] = y[k] + (1 / 6) * h * (k1 + 2 * k2 + 2 * k3 + k4)
        x += h

    return y


if __name__ == "__main__":
    import doctest

    doctest.testmod()

=====================================

"""
Numerical integration or quadrature for a smooth function f with known values at x_i

This method is the classical approach of summing 'Equally Spaced Abscissas'

method 2:
"Simpson Rule"

"""


def method_2(boundary: list[int], steps: int) -> float:
    # "Simpson Rule"
    # int(f) = delta_x/2 * (b-a)/3*(f1 + 4f2 + 2f_3 + ... + fn)
    """
    Calculate the definite integral of a function using Simpson's Rule.
    :param boundary: A list containing the lower and upper bounds of integration.
    :param steps: The number of steps or resolution for the integration.
    :return: The approximate integral value.

    >>> round(method_2([0, 2, 4], 10), 10)
    2.6666666667
    >>> round(method_2([2, 0], 10), 10)
    -0.2666666667
    >>> round(method_2([-2, -1], 10), 10)
    2.172
    >>> round(method_2([0, 1], 10), 10)
    0.3333333333
    >>> round(method_2([0, 2], 10), 10)
    2.6666666667
    >>> round(method_2([0, 2], 100), 10)
    2.5621226667
    >>> round(method_2([0, 1], 1000), 10)
    0.3320026653
    >>> round(method_2([0, 2], 0), 10)
    Traceback (most recent call last):
        ...
    ZeroDivisionError: Number of steps must be greater than zero
    >>> round(method_2([0, 2], -10), 10)
    Traceback (most recent call last):
        ...
    ZeroDivisionError: Number of steps must be greater than zero
    """
    if steps <= 0:
        raise ZeroDivisionError("Number of steps must be greater than zero")

    h = (boundary[1] - boundary[0]) / steps
    a = boundary[0]
    b = boundary[1]
    x_i = make_points(a, b, h)
    y = 0.0
    y += (h / 3.0) * f(a)
    cnt = 2
    for i in x_i:
        y += (h / 3) * (4 - 2 * (cnt % 2)) * f(i)
        cnt += 1
    y += (h / 3.0) * f(b)
    return y


def make_points(a, b, h):
    x = a + h
    while x < (b - h):
        yield x
        x = x + h


def f(x):  # enter your function here
    y = (x - 0) * (x - 0)
    return y


def main():
    a = 0.0  # Lower bound of integration
    b = 1.0  # Upper bound of integration
    steps = 10.0  # number of steps or resolution
    boundary = [a, b]  # boundary of integration
    y = method_2(boundary, steps)
    print(f"y = {y}")


if __name__ == "__main__":
    import doctest

    doctest.testmod()
    main()

=============================================

from collections.abc import Callable


def bisection(function: Callable[[float], float], a: float, b: float) -> float:
    """
    finds where function becomes 0 in [a,b] using bolzano
    >>> bisection(lambda x: x ** 3 - 1, -5, 5)
    1.0000000149011612
    >>> bisection(lambda x: x ** 3 - 1, 2, 1000)
    Traceback (most recent call last):
        ...
    ValueError: could not find root in given interval.
    >>> bisection(lambda x: x ** 2 - 4 * x + 3, 0, 2)
    1.0
    >>> bisection(lambda x: x ** 2 - 4 * x + 3, 2, 4)
    3.0
    >>> bisection(lambda x: x ** 2 - 4 * x + 3, 4, 1000)
    Traceback (most recent call last):
        ...
    ValueError: could not find root in given interval.
    """
    start: float = a
    end: float = b
    if function(a) == 0:  # one of the a or b is a root for the function
        return a
    elif function(b) == 0:
        return b
    elif (
        function(a) * function(b) > 0
    ):  # if none of these are root and they are both positive or negative,
        # then this algorithm can't find the root
        raise ValueError("could not find root in given interval.")
    else:
        mid: float = start + (end - start) / 2.0
        while abs(start - mid) > 10**-7:  # until precisely equals to 10^-7
            if function(mid) == 0:
                return mid
            elif function(mid) * function(start) < 0:
                end = mid
            else:
                start = mid
            mid = start + (end - start) / 2.0
        return mid


def f(x: float) -> float:
    return x**3 - 2 * x - 5


if __name__ == "__main__":
    print(bisection(f, 1, 1000))

    import doctest

    doctest.testmod()
===============================

"""
@author: MatteoRaso
"""

from collections.abc import Callable
from math import pi, sqrt
from random import uniform
from statistics import mean


def pi_estimator(iterations: int):
    """
    An implementation of the Monte Carlo method used to find pi.
    1. Draw a 2x2 square centred at (0,0).
    2. Inscribe a circle within the square.
    3. For each iteration, place a dot anywhere in the square.
       a. Record the number of dots within the circle.
    4. After all the dots are placed, divide the dots in the circle by the total.
    5. Multiply this value by 4 to get your estimate of pi.
    6. Print the estimated and numpy value of pi
    """

    # A local function to see if a dot lands in the circle.
    def is_in_circle(x: float, y: float) -> bool:
        distance_from_centre = sqrt((x**2) + (y**2))
        # Our circle has a radius of 1, so a distance
        # greater than 1 would land outside the circle.
        return distance_from_centre <= 1

    # The proportion of guesses that landed in the circle
    proportion = mean(
        int(is_in_circle(uniform(-1.0, 1.0), uniform(-1.0, 1.0)))
        for _ in range(iterations)
    )
    # The ratio of the area for circle to square is pi/4.
    pi_estimate = proportion * 4
    print(f"The estimated value of pi is {pi_estimate}")
    print(f"The numpy value of pi is {pi}")
    print(f"The total error is {abs(pi - pi_estimate)}")


def area_under_curve_estimator(
    iterations: int,
    function_to_integrate: Callable[[float], float],
    min_value: float = 0.0,
    max_value: float = 1.0,
) -> float:
    """
    An implementation of the Monte Carlo method to find area under
       a single variable non-negative real-valued continuous function,
       say f(x), where x lies within a continuous bounded interval,
       say [min_value, max_value], where min_value and max_value are
       finite numbers
    1. Let x be a uniformly distributed random variable between min_value to
       max_value
    2. Expected value of f(x) =
       (integrate f(x) from min_value to max_value)/(max_value - min_value)
    3. Finding expected value of f(x):
        a. Repeatedly draw x from uniform distribution
        b. Evaluate f(x) at each of the drawn x values
        c. Expected value = average of the function evaluations
    4. Estimated value of integral = Expected value * (max_value - min_value)
    5. Returns estimated value
    """

    return mean(
        function_to_integrate(uniform(min_value, max_value)) for _ in range(iterations)
    ) * (max_value - min_value)


def area_under_line_estimator_check(
    iterations: int, min_value: float = 0.0, max_value: float = 1.0
) -> None:
    """
    Checks estimation error for area_under_curve_estimator function
    for f(x) = x where x lies within min_value to max_value
    1. Calls "area_under_curve_estimator" function
    2. Compares with the expected value
    3. Prints estimated, expected and error value
    """

    def identity_function(x: float) -> float:
        """
        Represents identity function
        >>> [function_to_integrate(x) for x in [-2.0, -1.0, 0.0, 1.0, 2.0]]
        [-2.0, -1.0, 0.0, 1.0, 2.0]
        """
        return x

    estimated_value = area_under_curve_estimator(
        iterations, identity_function, min_value, max_value
    )
    expected_value = (max_value * max_value - min_value * min_value) / 2

    print("******************")
    print(f"Estimating area under y=x where x varies from {min_value} to {max_value}")
    print(f"Estimated value is {estimated_value}")
    print(f"Expected value is {expected_value}")
    print(f"Total error is {abs(estimated_value - expected_value)}")
    print("******************")


def pi_estimator_using_area_under_curve(iterations: int) -> None:
    """
    Area under curve y = sqrt(4 - x^2) where x lies in 0 to 2 is equal to pi
    """

    def function_to_integrate(x: float) -> float:
        """
        Represents semi-circle with radius 2
        >>> [function_to_integrate(x) for x in [-2.0, 0.0, 2.0]]
        [0.0, 2.0, 0.0]
        """
        return sqrt(4.0 - x * x)

    estimated_value = area_under_curve_estimator(
        iterations, function_to_integrate, 0.0, 2.0
    )

    print("******************")
    print("Estimating pi using area_under_curve_estimator")
    print(f"Estimated value is {estimated_value}")
    print(f"Expected value is {pi}")
    print(f"Total error is {abs(estimated_value - pi)}")
    print("******************")


if __name__ == "__main__":
    import doctest

    doctest.testmod()

=================================

"""
Reference: https://en.wikipedia.org/wiki/Gaussian_function
"""

from numpy import exp, pi, sqrt


def gaussian(x, mu: float = 0.0, sigma: float = 1.0) -> float:
    """
    >>> float(gaussian(1))
    0.24197072451914337

    >>> float(gaussian(24))
    3.342714441794458e-126

    >>> float(gaussian(1, 4, 2))
    0.06475879783294587

    >>> float(gaussian(1, 5, 3))
    0.05467002489199788

    Supports NumPy Arrays
    Use numpy.meshgrid with this to generate gaussian blur on images.
    >>> import numpy as np
    >>> x = np.arange(15)
    >>> gaussian(x)
    array([3.98942280e-01, 2.41970725e-01, 5.39909665e-02, 4.43184841e-03,
           1.33830226e-04, 1.48671951e-06, 6.07588285e-09, 9.13472041e-12,
           5.05227108e-15, 1.02797736e-18, 7.69459863e-23, 2.11881925e-27,
           2.14638374e-32, 7.99882776e-38, 1.09660656e-43])

    >>> float(gaussian(15))
    5.530709549844416e-50

    >>> gaussian([1,2, 'string'])
    Traceback (most recent call last):
        ...
    TypeError: unsupported operand type(s) for -: 'list' and 'float'

    >>> gaussian('hello world')
    Traceback (most recent call last):
        ...
    TypeError: unsupported operand type(s) for -: 'str' and 'float'

    >>> gaussian(10**234) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    OverflowError: (34, 'Result too large')

    >>> float(gaussian(10**-326))
    0.3989422804014327

    >>> float(gaussian(2523, mu=234234, sigma=3425))
    0.0
    """
    return 1 / sqrt(2 * pi * sigma**2) * exp(-((x - mu) ** 2) / (2 * sigma**2))


if __name__ == "__main__":
    import doctest

    doctest.testmod()


===============================================

"""
Binary Exponentiation

This is a method to find a^b in O(log b) time complexity and is one of the most commonly
used methods of exponentiation. The method is also useful for modular exponentiation,
when the solution to (a^b) % c is required.

To calculate a^b:
- If b is even, then a^b = (a * a)^(b / 2)
- If b is odd, then a^b = a * a^(b - 1)
Repeat until b = 1 or b = 0

For modular exponentiation, we use the fact that (a * b) % c = ((a % c) * (b % c)) % c
"""


def binary_exp_recursive(base: float, exponent: int) -> float:
    """
    Computes a^b recursively, where a is the base and b is the exponent

    >>> binary_exp_recursive(3, 5)
    243
    >>> binary_exp_recursive(11, 13)
    34522712143931
    >>> binary_exp_recursive(-1, 3)
    -1
    >>> binary_exp_recursive(0, 5)
    0
    >>> binary_exp_recursive(3, 1)
    3
    >>> binary_exp_recursive(3, 0)
    1
    >>> binary_exp_recursive(1.5, 4)
    5.0625
    >>> binary_exp_recursive(3, -1)
    Traceback (most recent call last):
        ...
    ValueError: Exponent must be a non-negative integer
    """
    if exponent < 0:
        raise ValueError("Exponent must be a non-negative integer")

    if exponent == 0:
        return 1

    if exponent % 2 == 1:
        return binary_exp_recursive(base, exponent - 1) * base

    b = binary_exp_recursive(base, exponent // 2)
    return b * b


def binary_exp_iterative(base: float, exponent: int) -> float:
    """
    Computes a^b iteratively, where a is the base and b is the exponent

    >>> binary_exp_iterative(3, 5)
    243
    >>> binary_exp_iterative(11, 13)
    34522712143931
    >>> binary_exp_iterative(-1, 3)
    -1
    >>> binary_exp_iterative(0, 5)
    0
    >>> binary_exp_iterative(3, 1)
    3
    >>> binary_exp_iterative(3, 0)
    1
    >>> binary_exp_iterative(1.5, 4)
    5.0625
    >>> binary_exp_iterative(3, -1)
    Traceback (most recent call last):
        ...
    ValueError: Exponent must be a non-negative integer
    """
    if exponent < 0:
        raise ValueError("Exponent must be a non-negative integer")

    res: int | float = 1
    while exponent > 0:
        if exponent & 1:
            res *= base

        base *= base
        exponent >>= 1

    return res


def binary_exp_mod_recursive(base: float, exponent: int, modulus: int) -> float:
    """
    Computes a^b % c recursively, where a is the base, b is the exponent, and c is the
    modulus

    >>> binary_exp_mod_recursive(3, 4, 5)
    1
    >>> binary_exp_mod_recursive(11, 13, 7)
    4
    >>> binary_exp_mod_recursive(1.5, 4, 3)
    2.0625
    >>> binary_exp_mod_recursive(7, -1, 10)
    Traceback (most recent call last):
        ...
    ValueError: Exponent must be a non-negative integer
    >>> binary_exp_mod_recursive(7, 13, 0)
    Traceback (most recent call last):
        ...
    ValueError: Modulus must be a positive integer
    """
    if exponent < 0:
        raise ValueError("Exponent must be a non-negative integer")
    if modulus <= 0:
        raise ValueError("Modulus must be a positive integer")

    if exponent == 0:
        return 1

    if exponent % 2 == 1:
        return (binary_exp_mod_recursive(base, exponent - 1, modulus) * base) % modulus

    r = binary_exp_mod_recursive(base, exponent // 2, modulus)
    return (r * r) % modulus


def binary_exp_mod_iterative(base: float, exponent: int, modulus: int) -> float:
    """
    Computes a^b % c iteratively, where a is the base, b is the exponent, and c is the
    modulus

    >>> binary_exp_mod_iterative(3, 4, 5)
    1
    >>> binary_exp_mod_iterative(11, 13, 7)
    4
    >>> binary_exp_mod_iterative(1.5, 4, 3)
    2.0625
    >>> binary_exp_mod_iterative(7, -1, 10)
    Traceback (most recent call last):
        ...
    ValueError: Exponent must be a non-negative integer
    >>> binary_exp_mod_iterative(7, 13, 0)
    Traceback (most recent call last):
        ...
    ValueError: Modulus must be a positive integer
    """
    if exponent < 0:
        raise ValueError("Exponent must be a non-negative integer")
    if modulus <= 0:
        raise ValueError("Modulus must be a positive integer")

    res: int | float = 1
    while exponent > 0:
        if exponent & 1:
            res = ((res % modulus) * (base % modulus)) % modulus

        base *= base
        exponent >>= 1

    return res


if __name__ == "__main__":
    from timeit import timeit

    a = 1269380576
    b = 374
    c = 34

    runs = 100_000
    print(
        timeit(
            f"binary_exp_recursive({a}, {b})",
            setup="from __main__ import binary_exp_recursive",
            number=runs,
        )
    )
    print(
        timeit(
            f"binary_exp_iterative({a}, {b})",
            setup="from __main__ import binary_exp_iterative",
            number=runs,
        )
    )
    print(
        timeit(
            f"binary_exp_mod_recursive({a}, {b}, {c})",
            setup="from __main__ import binary_exp_mod_recursive",
            number=runs,
        )
    )
    print(
        timeit(
            f"binary_exp_mod_iterative({a}, {b}, {c})",
            setup="from __main__ import binary_exp_mod_iterative",
            number=runs,
        )
    )

=============================================

"""
Extended Euclidean Algorithm.

Finds 2 numbers a and b such that it satisfies
the equation am + bn = gcd(m, n) (a.k.a Bezout's Identity)

https://en.wikipedia.org/wiki/Extended_Euclidean_algorithm
"""

# @Author: S. Sharma <silentcat>
# @Date:   2019-02-25T12:08:53-06:00
# @Email:  silentcat@protonmail.com
# @Last modified by:   pikulet
# @Last modified time: 2020-10-02
from __future__ import annotations

import sys


def extended_euclidean_algorithm(a: int, b: int) -> tuple[int, int]:
    """
    Extended Euclidean Algorithm.

    Finds 2 numbers a and b such that it satisfies
    the equation am + bn = gcd(m, n) (a.k.a Bezout's Identity)

    >>> extended_euclidean_algorithm(1, 24)
    (1, 0)

    >>> extended_euclidean_algorithm(8, 14)
    (2, -1)

    >>> extended_euclidean_algorithm(240, 46)
    (-9, 47)

    >>> extended_euclidean_algorithm(1, -4)
    (1, 0)

    >>> extended_euclidean_algorithm(-2, -4)
    (-1, 0)

    >>> extended_euclidean_algorithm(0, -4)
    (0, -1)

    >>> extended_euclidean_algorithm(2, 0)
    (1, 0)

    """
    # base cases
    if abs(a) == 1:
        return a, 0
    elif abs(b) == 1:
        return 0, b

    old_remainder, remainder = a, b
    old_coeff_a, coeff_a = 1, 0
    old_coeff_b, coeff_b = 0, 1

    while remainder != 0:
        quotient = old_remainder // remainder
        old_remainder, remainder = remainder, old_remainder - quotient * remainder
        old_coeff_a, coeff_a = coeff_a, old_coeff_a - quotient * coeff_a
        old_coeff_b, coeff_b = coeff_b, old_coeff_b - quotient * coeff_b

    # sign correction for negative numbers
    if a < 0:
        old_coeff_a = -old_coeff_a
    if b < 0:
        old_coeff_b = -old_coeff_b

    return old_coeff_a, old_coeff_b


def main():
    """Call Extended Euclidean Algorithm."""
    if len(sys.argv) < 3:
        print("2 integer arguments required")
        return 1
    a = int(sys.argv[1])
    b = int(sys.argv[2])
    print(extended_euclidean_algorithm(a, b))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

=================================================


