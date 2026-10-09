"""Calendar platform for WCM-COM weekly time programs."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .time_program import PROGRAM_NAMES, WEEKDAYS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one calendar per device-backed weekly program."""

    manager = hass.data[DOMAIN][entry.entry_id]["time_program_manager"]
    async_add_entities(
        WeishauptTimeProgramCalendar(manager, circuit, program)
        for circuit in (1, 2)
        for program in PROGRAM_NAMES
    )


class WeishauptTimeProgramCalendar(CalendarEntity):
    """Expose a recurring WCM-COM weekly program as a calendar."""

    _attr_should_poll = False
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, manager, heating_circuit: int, program: str) -> None:
        self._manager = manager
        self._heating_circuit = heating_circuit
        self._program = program
        self._attr_name = f"HK{heating_circuit} {PROGRAM_NAMES[program]}"
        self._attr_unique_id = (
            f"weishaupt_hk{heating_circuit}_{program}_time_program"
        )
        self._event: CalendarEvent | None = None

    @property
    def event(self) -> CalendarEvent | None:
        """Return the active or next event from the last loaded schedule."""

        return self._event

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return expanded weekly events in the requested local date range."""

        schedule = await self._manager.async_get(
            self._heating_circuit, self._program
        )
        events = self._expand(schedule, start_date, end_date)

        now = dt_util.now()
        state_events = self._expand(
            schedule,
            now - timedelta(days=1),
            now + timedelta(days=8),
        )
        self._event = next(
            (event for event in state_events if event.end > now),
            None,
        )
        if self.hass is not None and self.entity_id is not None:
            self.async_write_ha_state()
        return events

    def _expand(
        self,
        schedule: dict,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Expand the recurring weekly data without doing I/O."""

        events: list[CalendarEvent] = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            weekday = WEEKDAYS[current_date.weekday()]
            for slot, (start, end) in enumerate(schedule.get(weekday, ()), start=1):
                start_hour, start_minute = (int(part) for part in start.split(":"))
                end_hour, end_minute = (int(part) for part in end.split(":"))
                event_start = datetime.combine(
                    current_date,
                    datetime.min.time(),
                    tzinfo=start_date.tzinfo,
                ) + timedelta(hours=start_hour, minutes=start_minute)
                event_end = datetime.combine(
                    current_date,
                    datetime.min.time(),
                    tzinfo=start_date.tzinfo,
                ) + timedelta(hours=end_hour, minutes=end_minute)
                if event_end <= start_date or event_start >= end_date:
                    continue
                events.append(
                    CalendarEvent(
                        start=event_start,
                        end=event_end,
                        summary=self._attr_name,
                        description=f"Zeitfenster {slot} · {weekday}",
                        uid=(
                            f"wcm-{self._heating_circuit}-{self._program}-"
                            f"{weekday}-{slot}"
                        ),
                    )
                )
            current_date += timedelta(days=1)
        return sorted(events, key=lambda event: event.start)
