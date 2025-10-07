from __future__ import annotations

from enum import Enum


class MarketRegime(Enum):
    LOW_VOL_BULL = 0
    HIGH_VOL_BULL = 1
    LOW_VOL_BEAR = 2
    HIGH_VOL_BEAR = 3
    RANGING = 4
    UNKNOWN = 5
