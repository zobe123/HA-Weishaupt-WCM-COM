"""Async cache and write coordinator for WCM-COM time programs."""

from __future__ import annotations

import asyncio
from time import monotonic

from .time_program import encode_day
from .weishaupt_api import WeishauptAPI


class TimeProgramManager:
    """Load schedules on demand without adding them to the normal minute poll."""

    def __init__(self, hass, api: WeishauptAPI, cache_seconds: int = 300) -> None:
        self._hass = hass
        self._api = api
        self._cache_seconds = cache_seconds
        self._cache: dict[tuple[int, str], tuple[float, dict]] = {}
        self._lock = asyncio.Lock()

    async def async_get(self, heating_circuit: int, program: str) -> dict:
        """Return a cached schedule or read it from the controller."""

        key = (int(heating_circuit), str(program))
        cached = self._cache.get(key)
        if cached and monotonic() - cached[0] < self._cache_seconds:
            return cached[1]

        async with self._lock:
            cached = self._cache.get(key)
            if cached and monotonic() - cached[0] < self._cache_seconds:
                return cached[1]
            schedule = await self._hass.async_add_executor_job(
                self._api.read_time_program, key[0], key[1]
            )
            self._cache[key] = (monotonic(), schedule)
            return schedule

    async def async_set_day(
        self,
        heating_circuit: int,
        program: str,
        day: str,
        intervals,
    ) -> None:
        """Validate, atomically write and verify a full program day."""

        encoded = encode_day(intervals)
        await self._hass.async_add_executor_job(
            self._api.write_time_program_day,
            int(heating_circuit),
            str(program),
            str(day),
            encoded,
        )
        self._cache.pop((int(heating_circuit), str(program)), None)

    async def async_copy_day(
        self,
        source_circuit: int,
        source_program: str,
        source_day: str,
        target_circuit: int,
        target_program: str,
        target_days: list[str],
    ) -> None:
        """Copy one source day to one or more target days."""

        source = await self.async_get(source_circuit, source_program)
        intervals = source[source_day]
        for target_day in target_days:
            await self.async_set_day(
                target_circuit, target_program, target_day, intervals
            )

    def invalidate(self) -> None:
        """Discard all cached schedules."""

        self._cache.clear()
