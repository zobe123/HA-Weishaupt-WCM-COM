"""Weishaupt WCM-COM integration.

Uses a DataUpdateCoordinator to ensure that only a single
request to the WCM-COM device is executed per update interval.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    CONF_ALLOW_WRITE,
    DEFAULT_ALLOW_WRITE,
    CONF_ALLOW_FIRMWARE_CHECK,
    DEFAULT_ALLOW_FIRMWARE_CHECK,
    CONF_ADVANCED_LOGGING,
    DEFAULT_ADVANCED_LOGGING,
    CONF_SHOW_TIME_PROGRAM_PANEL,
    DEFAULT_SHOW_TIME_PROGRAM_PANEL,
    CONF_EXPOSE_TIME_PROGRAM_CALENDARS,
    DEFAULT_EXPOSE_TIME_PROGRAM_CALENDARS,
    CONF_EXTERNAL_GAS_METER_ENTITY,
    DEFAULT_EXTERNAL_GAS_METER_ENTITY,
    CONF_BOILER_PROFILE,
    DEFAULT_BOILER_PROFILE,
    BOILER_PROFILE_WTC_G,
    BOILER_PROFILE_WTC_OB,
    HEATING_CIRCUIT_PROBE_PARAMETERS,
    parameters_for_profile,
    detected_heating_circuit_buses,
    CONNECTION_DATA_KEYS,
    PARAMETERS,
    WRITE_BACKED_PARAMETER_NAMES,
    normalize_host,
)
from .weishaupt_api import WeishauptAPI, WeishauptAuthenticationError
from .time_program_manager import TimeProgramManager
from .frontend import async_register_frontend, async_unregister_frontend

_LOGGER = logging.getLogger(__name__)

BASE_PLATFORMS: list[str] = ["sensor", "select", "number"]

FIRMWARE_UPDATE_UNIQUE_ID = "weishaupt_wcm_com_firmware"
OPTIONAL_CALENDAR_UNIQUE_IDS = {
    "weishaupt_hk1_active_heating_program",
    "weishaupt_hk2_active_heating_program",
    "weishaupt_hot_water_time_program",
    "weishaupt_circulation_time_program",
}

HIDDEN_DUPLICATE_HOT_WATER_NUMBER_UNIQUE_IDS = {
    f"weishaupt_hk{heating_circuit}_user_{level}_ww_soll_number"
    for heating_circuit in (1, 2)
    for level in ("normal", "absenk")
}

DISABLED_TECHNICAL_HOT_WATER_UNIQUE_IDS = {
    "sensor": {
        f"weishaupt_{prefix}_user_{level}_ww_soll"
        for prefix in ("wtc_hk1", "hk1", "hk2")
        for level in ("normal", "absenk")
    },
    "number": set(HIDDEN_DUPLICATE_HOT_WATER_NUMBER_UNIQUE_IDS),
}

OBSOLETE_ENTITY_UNIQUE_IDS = {
    "sensor": {
        "weishaupt_wcm_com_installed_firmware",
        "weishaupt_hk1_user_sollwert_solar",
        "weishaupt_hk2_user_sollwert_solar",
        "weishaupt_hk1_user_betriebsart_hk",
        "weishaupt_hk1_user_betriebsart_ww",
        "weishaupt_hk2_user_betriebsart_hk",
        "weishaupt_hk2_user_betriebsart_ww",
    },
    "number": {
        "weishaupt_hk1_user_sollwert_solar_number",
        "weishaupt_hk2_user_sollwert_solar_number",
    },
    "select": {
        "weishaupt_hk1_user_op_mode_hk_select",
        "weishaupt_hk1_user_op_mode_ww_select",
        "weishaupt_hk2_user_op_mode_hk_select",
        "weishaupt_hk2_user_op_mode_ww_select",
    },
    "calendar": {
        f"weishaupt_hk{heating_circuit}_{program}_time_program"
        for heating_circuit in (1, 2)
        for program in (
            "heating_1",
            "heating_2",
            "heating_3",
            "hot_water",
            "circulation",
        )
    },
}


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate registry presentation without changing stable entity IDs."""

    if entry.version < 2:
        registry = er.async_get(hass)
        for parameter_name in WRITE_BACKED_PARAMETER_NAMES:
            unique_id = f"weishaupt_{parameter_name.lower().replace(' ', '_')}"
            entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
            if entity_id is None:
                continue
            registry_entry = registry.async_get(entity_id)
            if registry_entry is not None and registry_entry.hidden_by is None:
                registry.async_update_entity(
                    entity_id,
                    hidden_by=er.RegistryEntryHider.INTEGRATION,
                )

        hass.config_entries.async_update_entry(entry, version=2)

    if entry.version < 3:
        registry = er.async_get(hass)
        for unique_id in HIDDEN_DUPLICATE_HOT_WATER_NUMBER_UNIQUE_IDS:
            entity_id = registry.async_get_entity_id("number", DOMAIN, unique_id)
            if entity_id is None:
                continue
            registry_entry = registry.async_get(entity_id)
            if registry_entry is not None and registry_entry.hidden_by is None:
                registry.async_update_entity(
                    entity_id,
                    hidden_by=er.RegistryEntryHider.INTEGRATION,
                )

        hass.config_entries.async_update_entry(entry, version=3)

    if entry.version < 4:
        registry = er.async_get(hass)
        for platform, unique_ids in DISABLED_TECHNICAL_HOT_WATER_UNIQUE_IDS.items():
            for unique_id in unique_ids:
                entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
                if entity_id is None:
                    continue
                registry_entry = registry.async_get(entity_id)
                if registry_entry is not None and registry_entry.disabled_by is None:
                    registry.async_update_entity(
                        entity_id,
                        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
                    )

        hass.config_entries.async_update_entry(entry, version=4)

    if entry.version < 5:
        update_kwargs: dict[str, object] = {"version": 5}
        host = entry.options.get(CONF_HOST, entry.data.get(CONF_HOST))
        if entry.unique_id is None and host:
            update_kwargs["unique_id"] = normalize_host(host)
        hass.config_entries.async_update_entry(entry, **update_kwargs)

    if entry.version < 6:
        data = dict(entry.data)
        options = dict(entry.options)
        for key in CONNECTION_DATA_KEYS:
            if key in options:
                data[key] = options.pop(key)

        update_kwargs = {
            "version": 6,
            "data": data,
            "options": options,
        }
        host = data.get(CONF_HOST)
        if host:
            data[CONF_HOST] = normalize_host(host)
        if entry.unique_id is None and host:
            update_kwargs["unique_id"] = normalize_host(host)
        hass.config_entries.async_update_entry(entry, **update_kwargs)

    if entry.version < 7:
        options = dict(entry.options)
        # Existing installations historically queried the WTC-G set. Keep
        # that exact behavior until the owner explicitly selects a profile.
        options.setdefault(CONF_BOILER_PROFILE, BOILER_PROFILE_WTC_G)
        hass.config_entries.async_update_entry(entry, version=7, options=options)

    if entry.version < 8:
        options = dict(entry.options)
        # 1.5.0b1/b2 offered an unreliable automatic profile. Existing
        # installations historically used WTC-G, so migrate that legacy
        # value deterministically while preserving an explicit WTC-OB choice.
        if options.get(CONF_BOILER_PROFILE) not in (
            BOILER_PROFILE_WTC_G,
            BOILER_PROFILE_WTC_OB,
        ):
            options[CONF_BOILER_PROFILE] = BOILER_PROFILE_WTC_G
        hass.config_entries.async_update_entry(entry, version=8, options=options)

    return True


def _remove_obsolete_entities(
    hass: HomeAssistant,
    data: dict,
    *,
    remove_optional_calendars: bool = False,
    parameters: list[dict] | None = None,
) -> None:
    """Remove invalid and unsupported conditional registry entries."""

    registry = er.async_get(hass)
    unique_ids_by_platform = {
        platform: set(unique_ids)
        for platform, unique_ids in OBSOLETE_ENTITY_UNIQUE_IDS.items()
    }
    if remove_optional_calendars:
        unique_ids_by_platform["calendar"].update(OPTIONAL_CALENDAR_UNIQUE_IDS)
    for parameter in parameters or PARAMETERS:
        if not parameter.get("conditional") or parameter["name"] in data:
            continue
        slug = parameter["name"].lower().replace(" ", "_")
        unique_ids_by_platform["sensor"].add(f"weishaupt_{slug}")
        unique_ids_by_platform["number"].add(f"weishaupt_{slug}_number")
        if parameter["name"].endswith("Expert Raumthermostat"):
            if parameter["name"].startswith("WTC HK1"):
                select_slug = "wtc_hk1_expert_room_thermostat"
            elif parameter["name"].startswith("HK1"):
                select_slug = "hk1_expert_room_thermostat"
            else:
                select_slug = "hk2_expert_room_thermostat"
            unique_ids_by_platform["select"].add(
                f"weishaupt_{select_slug}_select"
            )

    for platform, unique_ids in unique_ids_by_platform.items():
        for unique_id in unique_ids:
            entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
            if entity_id is not None:
                registry.async_remove(entity_id)


def _remove_disabled_firmware_update_entity(hass: HomeAssistant) -> None:
    """Remove the optional firmware update entity when its check is disabled."""

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "update", DOMAIN, FIRMWARE_UPDATE_UNIQUE_ID
    )
    if entity_id is not None:
        registry.async_remove(entity_id)


def _remove_inactive_profile_entities(
    hass: HomeAssistant, active_parameters: list[dict]
) -> None:
    """Remove entities that belong exclusively to the inactive profile."""

    registry = er.async_get(hass)
    active_names = {parameter["name"] for parameter in active_parameters}
    inactive_names = {
        parameter["name"]
        for parameter in PARAMETERS
        if parameter.get("profile")
        and not parameter.get("internal")
        and not parameter.get("virtual")
        and parameter["name"] not in active_names
    }
    for name in inactive_names:
        slug = name.lower().replace(" ", "_")
        for platform, unique_id in (
            ("sensor", f"weishaupt_{slug}"),
            ("number", f"weishaupt_{slug}_number"),
        ):
            entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
            if entity_id is not None:
                registry.async_remove(entity_id)


def _parameter_unique_ids(parameter: dict) -> set[tuple[str, str]]:
    """Return registry entities whose state depends on one wire parameter."""

    if parameter.get("internal"):
        return set()
    name = str(parameter["name"])
    slug = name.lower().replace(" ", "_")
    unique_ids = {
        ("sensor", f"weishaupt_{slug}"),
        ("number", f"weishaupt_{slug}_number"),
    }
    select_suffixes = {
        "Config HK Type": "config_hk_type",
        "Config Regelvariante": "config_regelvariante",
        "Config Ext Room Sensor": "config_ext_room_sensor",
        "User Betriebsart": "user_op_mode",
        "Expert Reduziertbetrieb": "expert_reduced_mode",
        "Expert Raumthermostat": "expert_room_thermostat",
        "Urlaubstemperaturniveau": "urlaubstemperaturniveau",
    }
    for suffix, select_suffix in select_suffixes.items():
        if not name.endswith(suffix):
            continue
        if name.startswith("WTC HK1 "):
            prefix = "wtc_hk1"
        elif name.startswith("HK1 "):
            prefix = "hk1"
        elif name.startswith("HK2 "):
            prefix = "hk2"
        else:
            break
        unique_ids.add(("select", f"weishaupt_{prefix}_{select_suffix}_select"))
        break
    return unique_ids


def _filter_disabled_entity_parameters(
    hass: HomeAssistant,
    entry: ConfigEntry,
    parameters: list[dict],
) -> list[dict]:
    """Skip wire reads only when every registered consumer is disabled."""

    registry = er.async_get(hass)
    result = []
    for parameter in parameters:
        if parameter.get("internal") or parameter["name"] == "Status":
            result.append(parameter)
            continue
        consumers = []
        for platform, unique_id in _parameter_unique_ids(parameter):
            entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
            if entity_id is None:
                continue
            registry_entry = registry.async_get(entity_id)
            if registry_entry is not None and registry_entry.config_entry_id == entry.entry_id:
                consumers.append(registry_entry)
        # Unknown/new entities must be read once so their registry entries can
        # be created. A parameter is dropped only when all known consumers are
        # explicitly disabled.
        if not consumers or any(item.disabled_by is None for item in consumers):
            result.append(parameter)
    return result


def _remove_inactive_heating_circuit_entities(
    hass: HomeAssistant, active_buses: set[int]
) -> None:
    """Remove registry entries for heating circuits absent from the appliance."""

    registry = er.async_get(hass)
    inactive_prefixes = {
        0: ("weishaupt_wtc_hk1_", "weishaupt_kessel_config_version_fs"),
        1: ("weishaupt_hk1_",),
        2: ("weishaupt_hk2_",),
    }
    for registry_entry in list(registry.entities.values()):
        if registry_entry.platform != DOMAIN:
            continue
        for bus, prefixes in inactive_prefixes.items():
            if bus not in active_buses and registry_entry.unique_id.startswith(prefixes):
                registry.async_remove(registry_entry.entity_id)
                break
        if 1 not in active_buses and registry_entry.unique_id in (
            "weishaupt_hot_water_time_program",
            "weishaupt_circulation_time_program",
        ):
            registry.async_remove(registry_entry.entity_id)


def _register_entity_registry_reload_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Rebuild the read plan when an entity is enabled or disabled."""

    @callback
    def _handle_registry_update(event) -> None:
        if event.data.get("action") != "update":
            return
        if "disabled_by" not in event.data.get("changes", {}):
            return
        registry_entry = er.async_get(hass).async_get(event.data.get("entity_id"))
        if registry_entry is None or registry_entry.config_entry_id != entry.entry_id:
            return
        hass.async_create_task(
            hass.config_entries.async_reload(entry.entry_id),
            f"Reload {DOMAIN} after entity registry polling change",
        )

    entry.async_on_unload(
        hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, _handle_registry_update)
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Weishaupt WCM-COM from a config entry."""

    host: str | None = entry.data.get(CONF_HOST)
    username: str | None = entry.data.get(CONF_USERNAME)
    password: str | None = entry.data.get(CONF_PASSWORD)

    # Read scan interval, write flag and advanced logging from options (or use defaults)
    scan_interval: int = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    allow_write: bool = entry.options.get(CONF_ALLOW_WRITE, DEFAULT_ALLOW_WRITE)
    allow_firmware_check: bool = entry.options.get(
        CONF_ALLOW_FIRMWARE_CHECK, DEFAULT_ALLOW_FIRMWARE_CHECK
    )
    advanced_logging: bool = entry.options.get(CONF_ADVANCED_LOGGING, DEFAULT_ADVANCED_LOGGING)
    show_time_program_panel: bool = entry.options.get(
        CONF_SHOW_TIME_PROGRAM_PANEL, DEFAULT_SHOW_TIME_PROGRAM_PANEL
    )
    expose_time_program_calendars: bool = entry.options.get(
        CONF_EXPOSE_TIME_PROGRAM_CALENDARS,
        DEFAULT_EXPOSE_TIME_PROGRAM_CALENDARS,
    )
    external_gas_meter_entity: str = entry.options.get(
        CONF_EXTERNAL_GAS_METER_ENTITY,
        DEFAULT_EXTERNAL_GAS_METER_ENTITY,
    )
    requested_profile: str = entry.options.get(
        CONF_BOILER_PROFILE, DEFAULT_BOILER_PROFILE
    )
    platforms = [*BASE_PLATFORMS]
    if allow_firmware_check:
        platforms.append("update")
    if expose_time_program_calendars:
        platforms.append("calendar")

    active_profile = (
        requested_profile
        if requested_profile in (BOILER_PROFILE_WTC_G, BOILER_PROFILE_WTC_OB)
        else BOILER_PROFILE_WTC_G
    )
    circuit_detector = WeishauptAPI(
        host,
        username,
        password,
        advanced_logging=advanced_logging,
        parameters=HEATING_CIRCUIT_PROBE_PARAMETERS,
    )
    try:
        circuit_probe = await hass.async_add_executor_job(circuit_detector.get_data)
    except WeishauptAuthenticationError as err:
        raise ConfigEntryAuthFailed(
            "WCM-COM rejected the configured credentials"
        ) from err
    except Exception as err:  # pylint: disable=broad-except
        raise ConfigEntryNotReady(
            f"Could not discover WCM-COM heating circuits: {err}"
        ) from err
    active_heating_circuits = detected_heating_circuit_buses(circuit_probe)
    if not active_heating_circuits:
        raise ConfigEntryNotReady("WCM-COM returned no heating-circuit version")

    profile_parameters = parameters_for_profile(
        active_profile, active_heating_circuits
    )
    parameters = _filter_disabled_entity_parameters(
        hass, entry, profile_parameters
    )
    api = WeishauptAPI(
        host,
        username,
        password,
        advanced_logging=advanced_logging,
        parameters=parameters,
    )

    async def async_update_data() -> dict:
        """Fetch the latest data from the WCM-COM API.

        This function is executed by the DataUpdateCoordinator in an executor
        thread and must not block the event loop.
        """

        try:
            await hass.async_add_executor_job(api.update)
            return api.data
        except WeishauptAuthenticationError as err:
            raise ConfigEntryAuthFailed(
                "WCM-COM rejected the configured credentials"
            ) from err
        except Exception as err:  # pragma: no cover  # pylint: disable=broad-except
            raise UpdateFailed(f"Error communicating with WCM-COM: {err}") from err

    coordinator = DataUpdateCoordinator[
        dict
    ](
        hass,
        _LOGGER,
        name="weishaupt_wcm_com",
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )

    # First refresh before entities are created
    await coordinator.async_config_entry_first_refresh()
    _remove_obsolete_entities(
        hass,
        coordinator.data or {},
        remove_optional_calendars=not expose_time_program_calendars,
        parameters=parameters,
    )
    _remove_inactive_profile_entities(hass, profile_parameters)
    _remove_inactive_heating_circuit_entities(hass, active_heating_circuits)
    if not allow_firmware_check:
        _remove_disabled_firmware_update_entity(hass)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "time_program_manager": TimeProgramManager(hass, api),
        "allow_write": allow_write,
        "allow_firmware_check": allow_firmware_check,
        "advanced_logging": advanced_logging,
        "show_time_program_panel": show_time_program_panel,
        "expose_time_program_calendars": expose_time_program_calendars,
        "external_gas_meter_entity": external_gas_meter_entity,
        "requested_profile": requested_profile,
        "active_profile": active_profile,
        "active_heating_circuits": active_heating_circuits,
        "parameters": parameters,
        "platforms": platforms,
    }

    # Register services only once per integration domain
    if not hass.services.has_service(DOMAIN, "set_holiday_date"):
        _register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    _register_entity_registry_reload_listener(hass, entry)
    await async_register_frontend(
        hass,
        entry.entry_id,
        show_panel=show_time_program_panel,
    )

    return True


def _register_services(hass: HomeAssistant) -> None:
    """Register integration-level services (called once)."""

    def validation_error(key: str, **placeholders: object) -> ServiceValidationError:
        return ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key=key,
            translation_placeholders={
                name: str(value) for name, value in placeholders.items()
            },
        )

    def integration_error(key: str, **placeholders: object) -> HomeAssistantError:
        return HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key=key,
            translation_placeholders={
                name: str(value) for name, value in placeholders.items()
            },
        )

    async def async_set_holiday_date(call: ServiceCall) -> None:
        """Set HK1/HK2 holiday start/end date via raw Day/Month/Year parameters.

        Fields are mapped as:
        - HKx Holiday Start: IDs 283/284/285 (Day/Month/Year)
        - HKx Holiday End:   IDs 286/287/288 (Day/Month/Year)

        Year is encoded as (calendar year - 2000).
        A null/empty date resets Year to 0 and Day/Month to 1 ("not set").
        """

        heating_circuit = int(call.data.get("heating_circuit", 1))
        target = str(call.data.get("target", "start")).lower()
        date_str = call.data.get("date")

        if heating_circuit not in (0, 1, 2):
            raise validation_error("invalid_heating_circuit", value=heating_circuit)
        if target not in ("start", "end"):
            raise validation_error("invalid_holiday_target", value=target)

        # Determine parameter IDs for the selected HK/target
        if target == "start":
            base_id = 283
        else:
            base_id = 286

        day_id = base_id
        month_id = base_id + 1
        year_id = base_id + 2

        bus = heating_circuit
        modultyp = 6

        # Resolve the requested config entry. Never guess when multiple devices exist.
        domain_data = hass.data.get(DOMAIN, {})
        if not domain_data:
            raise integration_error("no_loaded_entry")

        config_entry_id = call.data.get("config_entry_id")
        if config_entry_id:
            entry_data = domain_data.get(config_entry_id)
            if entry_data is None:
                raise validation_error("unknown_entry", entry_id=config_entry_id)
        elif len(domain_data) == 1:
            entry_data = next(iter(domain_data.values()))
        else:
            raise validation_error("entry_required")

        if not entry_data.get("allow_write", False):
            raise integration_error("read_only")

        api: WeishauptAPI = entry_data["api"]
        coordinator: DataUpdateCoordinator = entry_data["coordinator"]

        # Parse date / reset logic
        if not date_str:
            # Reset: Year=0, Day=1, Month=1 (WebUI semantics for "not set")
            day = 1
            month = 1
            year_raw = 0
        else:
            from datetime import datetime

            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                raise validation_error("invalid_date", value=date_str) from None

            day = dt.day
            month = dt.month
            year_raw = dt.year - 2000
            if year_raw < 0 or year_raw > 99:
                raise validation_error("year_out_of_range", value=dt.year)

        _LOGGER.debug(
            "set_holiday_date: HK%s %s -> %s (Day=%s, Month=%s, YearRaw=%s)",
            heating_circuit,
            target,
            date_str or "<not set>",
            day,
            month,
            year_raw,
        )

        # Write all three fields under one API lock so no poll can observe a
        # half-updated date. Year is written last and activates the date.
        writes = [
            (day_id, bus, modultyp, day),
            (month_id, bus, modultyp, month),
            (year_id, bus, modultyp, year_raw),
        ]
        await hass.async_add_executor_job(api.write_parameters, writes)

        # Refresh coordinator so that HKx Holiday Start/End sensors update
        await coordinator.async_request_refresh()

    def resolve_writable_entry(call: ServiceCall) -> dict:
        """Resolve a loaded writable config entry without guessing."""

        domain_data = hass.data.get(DOMAIN, {})
        if not domain_data:
            raise integration_error("no_loaded_entry")
        config_entry_id = call.data.get("config_entry_id")
        if config_entry_id:
            entry_data = domain_data.get(config_entry_id)
            if entry_data is None:
                raise validation_error("unknown_entry", entry_id=config_entry_id)
        elif len(domain_data) == 1:
            entry_data = next(iter(domain_data.values()))
        else:
            raise validation_error("entry_required")
        if not entry_data.get("allow_write", False):
            raise integration_error("read_only")
        return entry_data

    async def async_set_time_program_day(call: ServiceCall) -> None:
        """Replace all three intervals of one time-program day."""

        entry_data = resolve_writable_entry(call)
        intervals = []
        for slot in range(1, 4):
            start = call.data.get(f"start_{slot}")
            end = call.data.get(f"end_{slot}")
            if bool(start) != bool(end):
                raise validation_error("incomplete_time_window", slot=slot)
            if start and end:
                intervals.append((start, end))

        try:
            await entry_data["time_program_manager"].async_set_day(
                int(call.data["heating_circuit"]),
                str(call.data["program"]),
                str(call.data["day"]),
                intervals,
            )
        except (ValueError, KeyError) as err:
            raise validation_error("invalid_time_program", reason=err) from err

    async def async_copy_time_program_day(call: ServiceCall) -> None:
        """Copy one source day to one or more target days."""

        entry_data = resolve_writable_entry(call)
        target_days = call.data["target_days"]
        if isinstance(target_days, str):
            target_days = [target_days]
        try:
            await entry_data["time_program_manager"].async_copy_day(
                int(call.data["source_heating_circuit"]),
                str(call.data["source_program"]),
                str(call.data["source_day"]),
                int(call.data["target_heating_circuit"]),
                str(call.data["target_program"]),
                list(target_days),
            )
        except (ValueError, KeyError) as err:
            raise validation_error("invalid_time_program", reason=err) from err

    async def async_clear_time_program_days(call: ServiceCall) -> None:
        """Disable all intervals on one or more program days."""

        entry_data = resolve_writable_entry(call)
        days = call.data["days"]
        if isinstance(days, str):
            days = [days]
        try:
            for day in days:
                await entry_data["time_program_manager"].async_set_day(
                    int(call.data["heating_circuit"]),
                    str(call.data["program"]),
                    str(day),
                    [],
                )
        except (ValueError, KeyError) as err:
            raise validation_error("invalid_time_program", reason=err) from err

    hass.services.async_register(DOMAIN, "set_holiday_date", async_set_holiday_date)
    hass.services.async_register(
        DOMAIN, "set_time_program_day", async_set_time_program_day
    )
    hass.services.async_register(
        DOMAIN, "copy_time_program_day", async_copy_time_program_day
    )
    hass.services.async_register(
        DOMAIN, "clear_time_program_days", async_clear_time_program_days
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    platforms = entry_data.get("platforms", [*BASE_PLATFORMS, "calendar"])
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        async_unregister_frontend(hass, entry.entry_id)
    return unload_ok
