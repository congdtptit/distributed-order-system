"""A replaceable clock: code reads the time through a Clock, never from the system directly.

Tests use FixedClock to control time (for example the X-hour limit of BR11).
"""

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """The current time, timezone-aware, in UTC."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """A clock that stays where it is put until moved."""

    def __init__(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise ValueError("FixedClock needs a timezone-aware time")
        self._at = at.astimezone(UTC)

    def now(self) -> datetime:
        return self._at

    def advance(self, delta: timedelta) -> None:
        self._at += delta
