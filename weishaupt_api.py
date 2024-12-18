"""Weishaupt API for WCM-COM communication."""
import logging
import json
import requests
import threading
from requests.auth import HTTPDigestAuth
from homeassistant.helpers.restore_state import RestoreEntity

from .const import PARAMETERS, ERROR_CODE_MAP, WARNING_CODE_MAP

_LOGGER = logging.getLogger(__name__)

# Lock initialisieren, um sicherzustellen, dass nur eine Anfrage gleichzeitig erfolgt
_lock = threading.Lock()

class WeishauptAPI(RestoreEntity):
    """API class for interacting with the Weishaupt WCM-COM."""

    def __init__(self, host, username=None, password=None):
        """Initialize the API."""
        self._host = host
        self._username = username
        self._password = password
        self._data = {}
        self.previous_values = {}
        self._state = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if (old_state := await self.async_get_last_state()) is not None:
            self._data = old_state.attributes.get("data", {})
            self.previous_values = old_state.attributes.get("previous_values", {})

    @property
    def data(self):
        """Return the latest data."""
        return self._data

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "data": self._data,
            "previous_values": self.previous_values
        }

    def update(self):
        """Fetch new data from the WCM-COM."""
        # Logik zur Datenabfrage mit Synchronisierung
        with _lock:
            self._fetch_data()

    def get_data(self):
        """Fetch and return data from WCM-COM (used for testing connectivity)."""
        # Verwende dieselbe Methode wie update(), um Daten abzurufen
        with _lock:
            self._fetch_data()
        return self._data

    def _fetch_data(self):
        """Actual data fetching logic."""
        _LOGGER.debug("Fetching new data")
        ENDPOINT = "/parameter.json"

        telegram = {
            'prot': 'coco',
            'telegramm': [[10, 0, 1, param["id"], 0, 0, 0, 0] for param in PARAMETERS],
        }

        url = f"http://{self._host}{ENDPOINT}"

        # Check if authentication is required
        if self._username and self._password:
            auth = HTTPDigestAuth(self._username, self._password)
        else:
            auth = None

        for attempt in range(3):  # Bis zu 3 Versuche, falls die Anfrage fehlschlägt
            try:
                req = requests.post(
                    url,
                    auth=auth,
                    data=json.dumps(telegram),
                    headers={'Content-Type': 'application/json'},
                    timeout=60  # Timeout auf 60 Sekunden erhöhen
                )
                req.raise_for_status()

                # Prüfen, ob die Antwort gültig ist
                if req.text.strip() == "":
                    _LOGGER.warning("Received empty response from Weishaupt WCM-COM, retrying...")
                    self._data = {}
                    continue  # Versuchen Sie es erneut

                # Prüfen, ob der Server überlastet ist (Server antwortet mit HTML)
                if "<HTML>" in req.text.upper():
                    _LOGGER.warning("Received 'server busy' response, retrying...")
                    self._data = {}
                    continue  # Versuchen Sie es erneut

                # Versuchen, die Antwort als JSON zu dekodieren
                try:
                    response_json = req.json()
                except json.JSONDecodeError as e:
                    _LOGGER.error(f"JSON decode error: {e}. Response content: {req.text}")
                    self._data = {}
                    continue  # Versuchen Sie es erneut

                # Verarbeiten der empfangenen Daten
                response_data = response_json.get("telegramm", [])
                _LOGGER.debug(f"Raw response data: {response_data}")
                result = {}

                for message in response_data:
                    param_id = message[3]
                    low_byte = message[6]
                    high_byte = message[7]
                    # Finden Sie den entsprechenden Parameter
                    param = next((p for p in PARAMETERS if p["id"] == param_id), None)
                    if param:
                        if param["type"] == "temperature":
                            value = self.get_temperature(low_byte, high_byte)
                            # Plausibilitätsprüfung für Temperaturwerte (z. B. -50 bis 150 °C)
                            if value < -50 or value > 150:
                                _LOGGER.warning(f"Unplausibler Temperaturwert verworfen: {value}")
                                value = self.previous_values.get(param["name"], value)
                        elif param["type"] == "value":
                            value = self.get_value(low_byte, high_byte)
                        elif param["type"] == "binary":
                            value = self.get_binary(low_byte, high_byte)
                        elif param["type"] == "code":
                            value = self.get_code(low_byte, high_byte)
                        else:
                            value = low_byte + 256 * high_byte  # Fallback

                        # Speichern Sie den neuen (oder beibehaltenen) Wert
                        result[param["name"]] = value
                        self.previous_values[param["name"]] = value

                _LOGGER.debug(f"Received data: {result}")
                self._data = result  # Speichern Sie die aktualisierten Daten
                return  # Erfolgreiches Ende der Schleife, Daten erfolgreich abgerufen

            except requests.exceptions.HTTPError as err:
                if req.status_code == 401:
                    _LOGGER.error("Authentication failed. Please check your username and password.")
                else:
                    _LOGGER.error(f"HTTP error occurred: {err}")
                self._data = {}
            except requests.exceptions.RequestException as e:
                _LOGGER.error(f"HTTP request error: {e}")
                self._data = {}
            except Exception as e:
                _LOGGER.error(f"Unexpected error: {e}")
                self._data = {}

        # Wenn alle Versuche fehlschlagen
        _LOGGER.error("Failed to fetch data from Weishaupt WCM-COM after multiple attempts.")
        self._data = {}

    def get_temperature(self, low_byte, high_byte):
        """Calculate temperature from two bytes."""
        raw_value = low_byte + 256 * high_byte
        if high_byte < 128:
            value = raw_value / 10
        else:
            value = (raw_value - 65536) / 10

        # Plausibilitätsprüfung erweitern
        if value < -50 or value > 150:
            _LOGGER.warning(f"Unplausibler Temperaturwert: {value}. Fallback auf vorherigen Wert.")
            return self.previous_values.get("fallback_temperature", 0)  # Standardwert als Fallback
        return value

    def get_value(self, low_byte, high_byte):
        """Calculate a value from two bytes."""
        return low_byte + 256 * high_byte

    def get_binary(self, low_byte, high_byte):
        """Return binary status as True or False."""
        return bool(low_byte + 256 * high_byte)

    def get_code(self, low_byte, high_byte):
        """Calculate a code value from two bytes."""
        return low_byte + 256 * high_byte

    def process_codes(self, code):
        """Process error and warning codes."""
        if code in ERROR_CODE_MAP:
            return ERROR_CODE_MAP[code]
        elif code in WARNING_CODE_MAP:
            return WARNING_CODE_MAP[code]
        else:
            return f"Unbekannter Code ({code})"

    def get_curl_command(self):
        """Generate a curl command for testing the API request."""
        ENDPOINT = "/parameter.json"
        url = f"http://{self._host}{ENDPOINT}"
        telegram = {
            'prot': 'coco',
            'telegramm': [[10, 0, 1, param["id"], 0, 0, 0, 0] for param in PARAMETERS],
        }
        headers = "-H 'Content-Type: application/json'"
        auth = f"--digest -u {self._username}:{self._password}" if self._username and self._password else ""
        data = f"-d '{json.dumps(telegram)}'"
        return f"curl -X POST {auth} {headers} {data} {url}"
