"""Calendar platform for WCM-COM weekly time programs."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .time_program import (
    PROGRAM_NAMES,
    WEEKDAYS,
    active_heating_program,
    circulation_supported,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one calendar per device-backed weekly program."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    manager = entry_data["time_program_manager"]
    coordinator = entry_data["coordinator"]
    entities: list[CalendarEntity] = [
        WeishauptActiveHeatingCalendar(manager, coordinator, circuit)
        for circuit in (1, 2)
    ]
    entities.append(
        WeishauptTimeProgramCalendar(
            manager,
            1,
            "hot_water",
            name="Warmwasser",
            unique_id="weishaupt_hot_water_time_program",
        )
    )
    if circulation_supported(coordinator.data or {}):
        entities.append(
            WeishauptTimeProgramCalendar(
                manager,
                1,
                "circulation",
                name="Zirkulation",
                unique_id="weishaupt_circulation_time_program",
            )
        )
    async_add_entities(entities)


class WeishauptTimeProgramCalendar(CalendarEntity):
    """Expose a recurring WCM-COM weekly program as a calendar."""

    _attr_should_poll = False
    _attr_icon = "mdi:calendar-clock"

    def __init__(
        self,
        manager,
        heating_circuit: int,
        program: str,
        *,
        name: str | None = None,
        unique_id: str | None = None,
    ) -> None:
        self._manager = manager
        self._heating_circuit = heating_circuit
        self._program = program
        self._attr_name = name or f"HK{heating_circuit} {PROGRAM_NAMES[program]}"
        self._attr_unique_id = unique_id or (
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

        schedule, program = await self._async_schedule()
        events = self._expand(schedule, start_date, end_date, program)

        now = dt_util.now()
        state_events = self._expand(
            schedule,
            now - timedelta(days=1),
            now + timedelta(days=8),
            program,
        )
        self._event = next(
            (event for event in state_events if event.end > now),
            None,
        )
        if self.hass is not None and self.entity_id is not None:
            self.async_write_ha_state()
        return events

    async def _async_schedule(self) -> tuple[dict, str]:
        """Return the schedule and program key represented by this entity."""

        return (
            await self._manager.async_get(self._heating_circuit, self._program),
            self._program,
        )

    def _expand(
        self,
        schedule: dict,
        start_date: datetime,
        end_date: datetime,
        program: str,
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
                            f"wcm-{self._heating_circuit}-{program}-"
                            f"{weekday}-{slot}"
                        ),
                    )
                )
            current_date += timedelta(days=1)
        return sorted(events, key=lambda event: event.start)


class WeishauptActiveHeatingCalendar(WeishauptTimeProgramCalendar):
    """Expose only the heating program currently selected on one circuit."""

    def __init__(self, manager, coordinator, heating_circuit: int) -> None:
        super().__init__(
            manager,
            heating_circuit,
            "heating_1",
            name=f"HK{heating_circuit} aktives Heizprogramm",
            unique_id=f"weishaupt_hk{heating_circuit}_active_heating_program",
        )
        self._coordinator = coordinator

    async def _async_schedule(self) -> tuple[dict, str]:
        program = active_heating_program(
            self._coordinator.data or {}, self._heating_circuit
        )
        if program is None:
            return ({day: () for day in WEEKDAYS}, "inactive")
        return (
            await self._manager.async_get(self._heating_circuit, program),
            program,
        )
