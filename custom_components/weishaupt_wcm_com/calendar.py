"""Calendar platform for WCM-COM weekly time programs."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .device_model import device_info
from .time_program import (
    WEEKDAYS,
    active_heating_program,
    circulation_program_bus,
    circulation_supported,
    domestic_hot_water_program_bus,
    heating_circuit_prefix,
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
    active_buses = entry_data.get("active_heating_circuits", {0, 1, 2})
    entities: list[CalendarEntity] = [
        WeishauptActiveHeatingCalendar(
            manager, coordinator, bus, language=hass.config.language
        )
        for bus in sorted(active_buses)
    ]
    data = coordinator.data or {}
    entities.append(
        WeishauptTimeProgramCalendar(
            manager,
            domestic_hot_water_program_bus(active_buses, data),
            "hot_water",
            translation_key="hot_water_program",
            unique_id="weishaupt_hot_water_time_program",
            language=hass.config.language,
        )
    )
    if circulation_supported(data):
        entities.append(
            WeishauptTimeProgramCalendar(
                manager,
                circulation_program_bus(active_buses, data),
                "circulation",
                translation_key="circulation_program",
                unique_id="weishaupt_circulation_time_program",
                language=hass.config.language,
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
        translation_key: str | None = None,
        unique_id: str | None = None,
        language: str = "en",
    ) -> None:
        self._manager = manager
        self._heating_circuit = heating_circuit
        self._program = program
        self._attr_has_entity_name = True
        self._attr_translation_key = translation_key or (
            f"hc{heating_circuit}_{program}"
        )
        self._attr_unique_id = unique_id or (
            f"weishaupt_hk{heating_circuit}_{program}_time_program"
        )
        german = language.lower().startswith("de")
        descriptions = {
            "hot_water": (
                "Wöchentliches Zeitprogramm für die Warmwasserbereitung.",
                "Weekly time program for domestic-hot-water heating.",
            ),
            "circulation": (
                "Wöchentliches Zeitprogramm für die Warmwasser-Zirkulation.",
                "Weekly time program for domestic-hot-water circulation.",
            ),
        }
        description = descriptions.get(
            program,
            (
                "Wöchentliches Zeitprogramm des Heizkreises.",
                "Weekly time program of the heating circuit.",
            ),
        )
        self._attr_extra_state_attributes = {
            "description": description[0] if german else description[1],
            "program_type": program,
            "wcm_heating_circuit": heating_circuit,
            "documentation_basis": (
                "Weishaupt-Handbuch / originale WCM-COM-WebUI"
                if german
                else "Weishaupt manual / original WCM-COM WebUI"
            ),
        }
        self._event: CalendarEvent | None = None

    @property
    def event(self) -> CalendarEvent | None:
        """Return the active or next event from the last loaded schedule."""

        return self._event

    @property
    def device_info(self):
        """Attach schedules to their functional Home Assistant device."""

        if self._program in {"hot_water", "circulation"}:
            return device_info("Warmwasser-Zeitprogramm")
        return device_info(
            f"{heating_circuit_prefix(self._heating_circuit)} Zeitprogramm"
        )

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
                        summary=self.name or self._attr_translation_key,
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

    def __init__(
        self,
        manager,
        coordinator,
        heating_circuit: int,
        *,
        language: str = "en",
    ) -> None:
        if heating_circuit == 0:
            translation_key = "wtc_hk1_active_heating_program"
            unique_id = "weishaupt_wtc_hk1_active_heating_program"
        else:
            translation_key = f"hc{heating_circuit}_active_heating_program"
            unique_id = f"weishaupt_hk{heating_circuit}_active_heating_program"
        super().__init__(
            manager,
            heating_circuit,
            "heating_1",
            translation_key=translation_key,
            unique_id=unique_id,
            language=language,
        )
        german = language.lower().startswith("de")
        self._attr_extra_state_attributes["description"] = (
            "Aktuell wirksames Heizprogramm; die Auswahl folgt der Betriebsart des Heizkreises."
            if german
            else "Currently effective heating program; selection follows the circuit operating mode."
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
