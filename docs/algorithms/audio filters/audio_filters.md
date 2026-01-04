from math import cos, sin, sqrt, tau

from audio_filters.iir_filter import IIRFilter

"""
Create 2nd-order IIR filters with Butterworth design.

Code based on https://webaudio.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html
Alternatively you can use scipy.signal.butter, which should yield the same results.
"""


def make_lowpass(
    frequency: int,
    samplerate: int,
    q_factor: float = 1 / sqrt(2),
) -> IIRFilter:
    """
    Creates a low-pass filter

    >>> filter = make_lowpass(1000, 48000)
    >>> filter.a_coeffs + filter.b_coeffs  # doctest: +NORMALIZE_WHITESPACE
    [1.0922959556412573, -1.9828897227476208, 0.9077040443587427, 0.004277569313094809,
     0.008555138626189618, 0.004277569313094809]
    """
    w0 = tau * frequency / samplerate
    _sin = sin(w0)
    _cos = cos(w0)
    alpha = _sin / (2 * q_factor)

    b0 = (1 - _cos) / 2
    b1 = 1 - _cos

    a0 = 1 + alpha
    a1 = -2 * _cos
    a2 = 1 - alpha

    filt = IIRFilter(2)
    filt.set_coefficients([a0, a1, a2], [b0, b1, b0])
    return filt


def make_highpass(
    frequency: int,
    samplerate: int,
    q_factor: float = 1 / sqrt(2),
) -> IIRFilter:
    """
    Creates a high-pass filter

    >>> filter = make_highpass(1000, 48000)
    >>> filter.a_coeffs + filter.b_coeffs  # doctest: +NORMALIZE_WHITESPACE
    [1.0922959556412573, -1.9828897227476208, 0.9077040443587427, 0.9957224306869052,
     -1.9914448613738105, 0.9957224306869052]
    """
    w0 = tau * frequency / samplerate
    _sin = sin(w0)
    _cos = cos(w0)
    alpha = _sin / (2 * q_factor)

    b0 = (1 + _cos) / 2
    b1 = -1 - _cos

    a0 = 1 + alpha
    a1 = -2 * _cos
    a2 = 1 - alpha

    filt = IIRFilter(2)
    filt.set_coefficients([a0, a1, a2], [b0, b1, b0])
    return filt


def make_bandpass(
    frequency: int,
    samplerate: int,
    q_factor: float = 1 / sqrt(2),
) -> IIRFilter:
    """
    Creates a band-pass filter

    >>> filter = make_bandpass(1000, 48000)
    >>> filter.a_coeffs + filter.b_coeffs  # doctest: +NORMALIZE_WHITESPACE
    [1.0922959556412573, -1.9828897227476208, 0.9077040443587427, 0.06526309611002579,
     0, -0.06526309611002579]
    """
    w0 = tau * frequency / samplerate
    _sin = sin(w0)
    _cos = cos(w0)
    alpha = _sin / (2 * q_factor)

    b0 = _sin / 2
    b1 = 0
    b2 = -b0

    a0 = 1 + alpha
    a1 = -2 * _cos
    a2 = 1 - alpha

    filt = IIRFilter(2)
    filt.set_coefficients([a0, a1, a2], [b0, b1, b2])
    return filt


def make_allpass(
    frequency: int,
    samplerate: int,
    q_factor: float = 1 / sqrt(2),
) -> IIRFilter:
    """
    Creates an all-pass filter

    >>> filter = make_allpass(1000, 48000)
    >>> filter.a_coeffs + filter.b_coeffs  # doctest: +NORMALIZE_WHITESPACE
    [1.0922959556412573, -1.9828897227476208, 0.9077040443587427, 0.9077040443587427,
     -1.9828897227476208, 1.0922959556412573]
    """
    w0 = tau * frequency / samplerate
    _sin = sin(w0)
    _cos = cos(w0)
    alpha = _sin / (2 * q_factor)

    b0 = 1 - alpha
    b1 = -2 * _cos
    b2 = 1 + alpha

    filt = IIRFilter(2)
    filt.set_coefficients([b2, b1, b0], [b0, b1, b2])
    return filt


def make_peak(
    frequency: int,
    samplerate: int,
    gain_db: float,
    q_factor: float = 1 / sqrt(2),
) -> IIRFilter:
    """
    Creates a peak filter

    >>> filter = make_peak(1000, 48000, 6)
    >>> filter.a_coeffs + filter.b_coeffs  # doctest: +NORMALIZE_WHITESPACE
    [1.0653405327119334, -1.9828897227476208, 0.9346594672880666, 1.1303715025601122,
     -1.9828897227476208, 0.8696284974398878]
    """
    w0 = tau * frequency / samplerate
    _sin = sin(w0)
    _cos = cos(w0)
    alpha = _sin / (2 * q_factor)
    big_a = 10 ** (gain_db / 40)

    b0 = 1 + alpha * big_a
    b1 = -2 * _cos
    b2 = 1 - alpha * big_a
    a0 = 1 + alpha / big_a
    a1 = -2 * _cos
    a2 = 1 - alpha / big_a

    filt = IIRFilter(2)
    filt.set_coefficients([a0, a1, a2], [b0, b1, b2])
    return filt


def make_lowshelf(
    frequency: int,
    samplerate: int,
    gain_db: float,
    q_factor: float = 1 / sqrt(2),
) -> IIRFilter:
    """
    Creates a low-shelf filter

    >>> filter = make_lowshelf(1000, 48000, 6)
    >>> filter.a_coeffs + filter.b_coeffs  # doctest: +NORMALIZE_WHITESPACE
    [3.0409336710888786, -5.608870992220748, 2.602157875636628, 3.139954022810743,
     -5.591841778072785, 2.5201667380627257]
    """
    w0 = tau * frequency / samplerate
    _sin = sin(w0)
    _cos = cos(w0)
    alpha = _sin / (2 * q_factor)
    big_a = 10 ** (gain_db / 40)
    pmc = (big_a + 1) - (big_a - 1) * _cos
    ppmc = (big_a + 1) + (big_a - 1) * _cos
    mpc = (big_a - 1) - (big_a + 1) * _cos
    pmpc = (big_a - 1) + (big_a + 1) * _cos
    aa2 = 2 * sqrt(big_a) * alpha

    b0 = big_a * (pmc + aa2)
    b1 = 2 * big_a * mpc
    b2 = big_a * (pmc - aa2)
    a0 = ppmc + aa2
    a1 = -2 * pmpc
    a2 = ppmc - aa2

    filt = IIRFilter(2)
    filt.set_coefficients([a0, a1, a2], [b0, b1, b2])
    return filt


def make_highshelf(
    frequency: int,
    samplerate: int,
    gain_db: float,
    q_factor: float = 1 / sqrt(2),
) -> IIRFilter:
    """
    Creates a high-shelf filter

    >>> filter = make_highshelf(1000, 48000, 6)
    >>> filter.a_coeffs + filter.b_coeffs  # doctest: +NORMALIZE_WHITESPACE
    [2.2229172136088806, -3.9587208137297303, 1.7841414181566304, 4.295432981120543,
     -7.922740859457287, 3.6756456963725253]
    """
    w0 = tau * frequency / samplerate
    _sin = sin(w0)
    _cos = cos(w0)
    alpha = _sin / (2 * q_factor)
    big_a = 10 ** (gain_db / 40)
    pmc = (big_a + 1) - (big_a - 1) * _cos
    ppmc = (big_a + 1) + (big_a - 1) * _cos
    mpc = (big_a - 1) - (big_a + 1) * _cos
    pmpc = (big_a - 1) + (big_a + 1) * _cos
    aa2 = 2 * sqrt(big_a) * alpha

    b0 = big_a * (ppmc + aa2)
    b1 = -2 * big_a * pmpc
    b2 = big_a * (ppmc - aa2)
    a0 = pmc + aa2
    a1 = 2 * mpc
    a2 = pmc - aa2

    filt = IIRFilter(2)
    filt.set_coefficients([a0, a1, a2], [b0, b1, b2])
    return filt

====================================

from __future__ import annotations


class IIRFilter:
    r"""
    N-Order IIR filter
    Assumes working with float samples normalized on [-1, 1]

    ---

    Implementation details:
    Based on the 2nd-order function from
    https://en.wikipedia.org/wiki/Digital_biquad_filter,
    this generalized N-order function was made.

    Using the following transfer function
        .. math:: H(z)=\frac{b_{0}+b_{1}z^{-1}+b_{2}z^{-2}+...+b_{k}z^{-k}}
                  {a_{0}+a_{1}z^{-1}+a_{2}z^{-2}+...+a_{k}z^{-k}}

    we can rewrite this to
        .. math:: y[n]={\frac{1}{a_{0}}}
                  \left(\left(b_{0}x[n]+b_{1}x[n-1]+b_{2}x[n-2]+...+b_{k}x[n-k]\right)-
                  \left(a_{1}y[n-1]+a_{2}y[n-2]+...+a_{k}y[n-k]\right)\right)
    """

    def __init__(self, order: int) -> None:
        self.order = order

        # a_{0} ... a_{k}
        self.a_coeffs = [1.0] + [0.0] * order
        # b_{0} ... b_{k}
        self.b_coeffs = [1.0] + [0.0] * order

        # x[n-1] ... x[n-k]
        self.input_history = [0.0] * self.order
        # y[n-1] ... y[n-k]
        self.output_history = [0.0] * self.order

    def set_coefficients(self, a_coeffs: list[float], b_coeffs: list[float]) -> None:
        """
        Set the coefficients for the IIR filter.
        These should both be of size `order` + 1.
        :math:`a_0` may be left out, and it will use 1.0 as default value.

        This method works well with scipy's filter design functions

        >>> # Make a 2nd-order 1000Hz butterworth lowpass filter
        >>> import scipy.signal
        >>> b_coeffs, a_coeffs = scipy.signal.butter(2, 1000,
        ...                                          btype='lowpass',
        ...                                          fs=48000)
        >>> filt = IIRFilter(2)
        >>> filt.set_coefficients(a_coeffs, b_coeffs)
        """
        if len(a_coeffs) < self.order:
            a_coeffs = [1.0, *a_coeffs]

        if len(a_coeffs) != self.order + 1:
            msg = (
                f"Expected a_coeffs to have {self.order + 1} elements "
                f"for {self.order}-order filter, got {len(a_coeffs)}"
            )
            raise ValueError(msg)

        if len(b_coeffs) != self.order + 1:
            msg = (
                f"Expected b_coeffs to have {self.order + 1} elements "
                f"for {self.order}-order filter, got {len(a_coeffs)}"
            )
            raise ValueError(msg)

        self.a_coeffs = a_coeffs
        self.b_coeffs = b_coeffs

    def process(self, sample: float) -> float:
        """
        Calculate :math:`y[n]`

        >>> filt = IIRFilter(2)
        >>> filt.process(0)
        0.0
        """
        result = 0.0

        # Start at index 1 and do index 0 at the end.
        for i in range(1, self.order + 1):
            result += (
                self.b_coeffs[i] * self.input_history[i - 1]
                - self.a_coeffs[i] * self.output_history[i - 1]
            )

        result = (result + self.b_coeffs[0] * sample) / self.a_coeffs[0]

        self.input_history[1:] = self.input_history[:-1]
        self.output_history[1:] = self.output_history[:-1]

        self.input_history[0] = sample
        self.output_history[0] = result

        return result

===================================

from __future__ import annotations

from abc import abstractmethod
from math import pi
from typing import Protocol

import matplotlib.pyplot as plt
import numpy as np


class FilterType(Protocol):
    @abstractmethod
    def process(self, sample: float) -> float:
        """
        Calculate y[n]

        >>> issubclass(FilterType, Protocol)
        True
        """


def get_bounds(
    fft_results: np.ndarray, samplerate: int
) -> tuple[int | float, int | float]:
    """
    Get bounds for printing fft results

    >>> import numpy
    >>> array = numpy.linspace(-20.0, 20.0, 1000)
    >>> get_bounds(array, 1000)
    (-20, 20)
    """
    lowest = min([-20, np.min(fft_results[1 : samplerate // 2 - 1])])
    highest = max([20, np.max(fft_results[1 : samplerate // 2 - 1])])
    return lowest, highest


def show_frequency_response(filter_type: FilterType, samplerate: int) -> None:
    """
    Show frequency response of a filter

    >>> from audio_filters.iir_filter import IIRFilter
    >>> filt = IIRFilter(4)
    >>> show_frequency_response(filt, 48000)
    """

    size = 512
    inputs = [1] + [0] * (size - 1)
    outputs = [filter_type.process(item) for item in inputs]

    filler = [0] * (samplerate - size)  # zero-padding
    outputs += filler
    fft_out = np.abs(np.fft.fft(outputs))
    fft_db = 20 * np.log10(fft_out)

    # Frequencies on log scale from 24 to nyquist frequency
    plt.xlim(24, samplerate / 2 - 1)
    plt.xlabel("Frequency (Hz)")
    plt.xscale("log")

    # Display within reasonable bounds
    bounds = get_bounds(fft_db, samplerate)
    plt.ylim(max([-80, bounds[0]]), min([80, bounds[1]]))
    plt.ylabel("Gain (dB)")

    plt.plot(fft_db)
    plt.show()


def show_phase_response(filter_type: FilterType, samplerate: int) -> None:
    """
    Show phase response of a filter

    >>> from audio_filters.iir_filter import IIRFilter
    >>> filt = IIRFilter(4)
    >>> show_phase_response(filt, 48000)
    """

    size = 512
    inputs = [1] + [0] * (size - 1)
    outputs = [filter_type.process(item) for item in inputs]

    filler = [0] * (samplerate - size)  # zero-padding
    outputs += filler
    fft_out = np.angle(np.fft.fft(outputs))

    # Frequencies on log scale from 24 to nyquist frequency
    plt.xlim(24, samplerate / 2 - 1)
    plt.xlabel("Frequency (Hz)")
    plt.xscale("log")

    plt.ylim(-2 * pi, 2 * pi)
    plt.ylabel("Phase shift (Radians)")
    plt.plot(np.unwrap(fft_out, -2 * pi))
    plt.show()

=======================

