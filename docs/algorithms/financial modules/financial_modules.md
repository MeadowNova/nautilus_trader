"""
Calculate the exponential moving average (EMA) on the series of stock prices.
Wikipedia Reference: https://en.wikipedia.org/wiki/Exponential_smoothing
https://www.investopedia.com/terms/e/ema.asp#toc-what-is-an-exponential
-moving-average-ema

Exponential moving average is used in finance to analyze changes stock prices.
EMA is used in conjunction with Simple moving average (SMA), EMA reacts to the
changes in the value quicker than SMA, which is one of the advantages of using EMA.
"""

from collections.abc import Iterator


def exponential_moving_average(
    stock_prices: Iterator[float], window_size: int
) -> Iterator[float]:
    """
    Yields exponential moving averages of the given stock prices.
    >>> tuple(exponential_moving_average(iter([2, 5, 3, 8.2, 6, 9, 10]), 3))
    (2, 3.5, 3.25, 5.725, 5.8625, 7.43125, 8.715625)

    :param stock_prices: A stream of stock prices
    :param window_size: The number of stock prices that will trigger a new calculation
                        of the exponential average (window_size > 0)
    :return: Yields a sequence of exponential moving averages

    Formula:

    st = alpha * xt + (1 - alpha) * st_prev

    Where,
    st : Exponential moving average at timestamp t
    xt : stock price in from the stock prices at timestamp t
    st_prev : Exponential moving average at timestamp t-1
    alpha : 2/(1 + window_size) - smoothing factor

    Exponential moving average (EMA) is a rule of thumb technique for
    smoothing time series data using an exponential window function.
    """

    if window_size <= 0:
        raise ValueError("window_size must be > 0")

    # Calculating smoothing factor
    alpha = 2 / (1 + window_size)

    # Exponential average at timestamp t
    moving_average = 0.0

    for i, stock_price in enumerate(stock_prices):
        if i <= window_size:
            # Assigning simple moving average till the window_size for the first time
            # is reached
            moving_average = (moving_average + stock_price) * 0.5 if i else stock_price
        else:
            # Calculating exponential moving average based on current timestamp data
            # point and previous exponential average value
            moving_average = (alpha * stock_price) + ((1 - alpha) * moving_average)
        yield moving_average


if __name__ == "__main__":
    import doctest

    doctest.testmod()

    stock_prices = [2.0, 5, 3, 8.2, 6, 9, 10]
    window_size = 3
    result = tuple(exponential_moving_average(iter(stock_prices), window_size))
    print(f"{stock_prices = }")
    print(f"{window_size = }")
    print(f"{result = }")


=========================

"""
The Simple Moving Average (SMA) is a statistical calculation used to analyze data points
by creating a constantly updated average price over a specific time period.
In finance, SMA is often used in time series analysis to smooth out price data
and identify trends.

Reference: https://en.wikipedia.org/wiki/Moving_average
"""

from collections.abc import Sequence


def simple_moving_average(
    data: Sequence[float], window_size: int
) -> list[float | None]:
    """
    Calculate the simple moving average (SMA) for some given time series data.

    :param data: A list of numerical data points.
    :param window_size: An integer representing the size of the SMA window.
    :return: A list of SMA values with the same length as the input data.

    Examples:
    >>> sma = simple_moving_average([10, 12, 15, 13, 14, 16, 18, 17, 19, 21], 3)
    >>> [round(value, 2) if value is not None else None for value in sma]
    [None, None, 12.33, 13.33, 14.0, 14.33, 16.0, 17.0, 18.0, 19.0]
    >>> simple_moving_average([10, 12, 15], 5)
    [None, None, None]
    >>> simple_moving_average([10, 12, 15, 13, 14, 16, 18, 17, 19, 21], 0)
    Traceback (most recent call last):
    ...
    ValueError: Window size must be a positive integer
    """
    if window_size < 1:
        raise ValueError("Window size must be a positive integer")

    sma: list[float | None] = []

    for i in range(len(data)):
        if i < window_size - 1:
            sma.append(None)  # SMA not available for early data points
        else:
            window = data[i - window_size + 1 : i + 1]
            sma_value = sum(window) / window_size
            sma.append(sma_value)
    return sma


if __name__ == "__main__":
    import doctest

    doctest.testmod()

    # Example data (replace with your own time series data)
    data = [10, 12, 15, 13, 14, 16, 18, 17, 19, 21]

    # Specify the window size for the SMA
    window_size = 3

    # Calculate the Simple Moving Average
    sma_values = simple_moving_average(data, window_size)

    # Print the SMA values
    print("Simple Moving Average (SMA) Values:")
    for i, value in enumerate(sma_values):
        if value is not None:
            print(f"Day {i + 1}: {value:.2f}")
        else:
            print(f"Day {i + 1}: Not enough data for SMA")


===================================

"""
Reference: https://www.investopedia.com/terms/p/presentvalue.asp

An algorithm that calculates the present value of a stream of yearly cash flows given...
1. The discount rate (as a decimal, not a percent)
2. An array of cash flows, with the index of the cash flow being the associated year

Note: This algorithm assumes that cash flows are paid at the end of the specified year
"""


def present_value(discount_rate: float, cash_flows: list[float]) -> float:
    """
    >>> present_value(0.13, [10, 20.70, -293, 297])
    4.69
    >>> present_value(0.07, [-109129.39, 30923.23, 15098.93, 29734,39])
    -42739.63
    >>> present_value(0.07, [109129.39, 30923.23, 15098.93, 29734,39])
    175519.15
    >>> present_value(-1, [109129.39, 30923.23, 15098.93, 29734,39])
    Traceback (most recent call last):
        ...
    ValueError: Discount rate cannot be negative
    >>> present_value(0.03, [])
    Traceback (most recent call last):
        ...
    ValueError: Cash flows list cannot be empty
    """
    if discount_rate < 0:
        raise ValueError("Discount rate cannot be negative")
    if not cash_flows:
        raise ValueError("Cash flows list cannot be empty")
    present_value = sum(
        cash_flow / ((1 + discount_rate) ** i) for i, cash_flow in enumerate(cash_flows)
    )
    return round(present_value, ndigits=2)


if __name__ == "__main__":
    import doctest

    doctest.testmod()

=================================
