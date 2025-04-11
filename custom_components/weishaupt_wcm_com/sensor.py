"""Platform for sensor integration."""
import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTemperature

from .const import (
    DOMAIN,
    NAME_PREFIX,
    PARAMETERS,
    ERROR_CODE_KEY,
    ERROR_CODE_MAP,
    WARNING_CODE_MAP,
    OPERATION_MODE_MAP,
    OPERATION_PHASE_MAP,
)
from .base_entity import WeishauptBaseEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform."""
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    scan_interval = hass.data[DOMAIN][entry.entry_id]["scan_interval"]

    sensors = []
    for param in PARAMETERS:
        sensor_name = param["name"]
        unit = UnitOfTemperature.CELSIUS if param["type"] == "temperature" else None
        sensors.append(WeishauptSensor(api, sensor_name, unit, scan_interval))

    async_add_entities(sensors)

class WeishauptSensor(WeishauptBaseEntity, SensorEntity):
    """Representation of a Weishaupt Sensor."""

    def __init__(self, api, sensor_name, unit, scan_interval):
        """Initialize the sensor."""
        super().__init__(api)
        self._sensor_name = sensor_name
        self._attr_name = f"{NAME_PREFIX}{self._sensor_name}"
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{DOMAIN}_{api.host}_{self._sensor_name.lower().replace(' ', '_')}"
        self._scan_interval = timedelta(seconds=scan_interval)
        self._attr_native_value = None

    @property
    def should_poll(self):
        """Return True as entity should be polled."""
        return True

    @property
    def scan_interval(self):
        """Return the scan interval."""
        return self._scan_interval

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await self.hass.async_add_executor_job(self._api.update)
        data = self._api.data
        try:
            value = data.get(self._sensor_name)
            if value is None:
                self._attr_native_value = None
                _LOGGER.debug(f"Data for {self._sensor_name} not found")
                return

            if self._sensor_name == ERROR_CODE_KEY:
                error_code = int(value)
                self._attr_native_value = ERROR_CODE_MAP.get(error_code, f"Unbekannter Fehler ({error_code})")
            elif self._sensor_name == "Betriebsmodus":
                self._attr_native_value = OPERATION_MODE_MAP.get(value, f"Unbekannter Modus ({value})")
            elif self._sensor_name == "Betriebsphase":
                self._attr_native_value = OPERATION_PHASE_MAP.get(value, f"Unbekannte Phase ({value})")
            else:
                param_type = next((p["type"] for p in PARAMETERS if p["name"] == self._sensor_name), None)
                self._attr_native_value = "Ein" if value and param_type == "binary" else "Aus" if param_type == "binary" else value
                    
            self._api.previous_values[self._sensor_name] = value
            
        except Exception as e:
            _LOGGER.error(f"Error updating sensor {self._sensor_name}: {e}")
            self._attr_native_value = None
