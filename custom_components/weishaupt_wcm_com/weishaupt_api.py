"""Weishaupt API for WCM-COM communication."""
import logging
import json
import requests
import threading
import time
from requests.auth import HTTPDigestAuth

from .const import PARAMETERS, ERROR_CODE_MAP, WARNING_CODE_MAP
from .protocol import (
    READ_COMMAND,
    WRITE_COMMAND,
    build_telegram as build_coco_telegram,
    parameter_protocol,
)
from .temperature import normalize_temperature_value

_LOGGER = logging.getLogger(__name__)

# Lock initialisieren, um sicherzustellen, dass nur eine Anfrage gleichzeitig erfolgt
_lock = threading.Lock()


class WeishauptCommunicationError(Exception):
    """Raised when a complete WCM-COM update or write cannot be completed."""


class WeishauptAPI:
    """API class for interacting with the Weishaupt WCM-COM."""

    def __init__(self, host, username=None, password=None, advanced_logging: bool = False):
        """Initialize the API."""
        self._host = host
        self._username = username
        self._password = password
        self._data = {}
        self.previous_values = {}
        # Optionaler Modus für zusätzliche Debug-Logs
        self.advanced_logging = advanced_logging

    @property
    def data(self):
        """Return the latest data."""
        return self._data

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

        # Build CoCo telegrams based on parameter metadata and original
        # Elster webApp format (see webApp.js / OBJTELEGRAMM).
        #
        # Index mapping:
        #   0: TEL_MODULTYP   (module type / destination)
        #   1: TEL_BUSKENNUNG (bus id / Heizkreis)
        #   2: TEL_COMMAND    (1 = read)
        #   3: TEL_INFONR     (parameter id)
        #   4: TEL_INDEX      (unused here)
        #   5: TEL_PROT       (unused here)
        #   6: TEL_DATA low   (0 for read)
        #   7: TEL_DATA high  (0 for read)

        def build_read_request(params):
            telegram = {"prot": "coco", "telegramm": []}
            for param in params:
                # Default behaviour (existing implementation): use destination=10
                # as module type and no specific bus assignment.
                modultyp = param.get("destination", 10)
                bus = 0

                # Special handling for Heizkreis-Prozesswerte where the original
                # web UI uses a concrete module type and bus id (HK1 = bus 1, ...).
                if "modultyp" in param:
                    modultyp = param["modultyp"]
                if "bus" in param:
                    bus = param["bus"]

                telegram["telegramm"].append(
                    build_coco_telegram(
                        module_type=modultyp,
                        bus=bus,
                        command=READ_COMMAND,
                        parameter_id=param["id"],
                        protocol=parameter_protocol(param),
                    )
                )
            return telegram

        # Split in mehrere Requests, damit der WCM-COM alle Telegramme
        # beantwortet (begrenzte Anzahl pro Antwort).
        #  - globale Prozesswerte (Kessel)
        #  - Heizkreis-Prozesswerte (HK1/HK2)
        #  - Heizkreis-Konfig-Parameter (Pumpen, Spannungen, HK-Typ, Ext. Fühler)
        #  - HK-User-Parameter (Betriebsarten & User-Temperaturen)
        #  - Fachmann-/Expert-Parameter (P10, P12, P18, ...)
        global_params = [
            p for p in PARAMETERS
            if "bus" not in p and "modultyp" not in p and not p["name"].startswith("Expert ") and not p.get("virtual")
        ]
        expert_params = [
            p for p in PARAMETERS
            if p["name"].startswith("Expert ")
        ]
        # Heizkreis-Prozesswerte (Temperaturen/Sollwerte) priorisieren, damit sie
        # bei begrenzter Telegrammzahl nicht von zusätzlichen Konfig/User-Parametern
        # verdrängt werden.
        hk_process_params = [
            p
            for p in PARAMETERS
            if ("bus" in p or "modultyp" in p)
            and not p["name"].startswith("HK1 Config")
            and not p["name"].startswith("HK2 Config")
            and not p["name"].startswith("HK1 User")
            and not p["name"].startswith("HK2 User")
            and not p.get("internal")
            and not p.get("virtual")
        ]

        # Spezielle Gruppe für HK1 Holiday Temp Level + System Date/Time + DST,
        # damit diese nicht in einem übervollen Prozess-Telegramm untergehen.
        date_params = [
            p
            for p in PARAMETERS
            if not p.get("virtual")
            and (
                p["name"].startswith("System Date ")
                or p["name"].startswith("System Time ")
                or p["name"].startswith("DST ")
                or p["name"] == "HK1 Holiday Temp Level"
            )
        ]
        # Versions-Parameter (FS/EM High/Low) separat abfragen, damit sie immer
        # vollständig geliefert werden.
        hk_version_params = [
            p
            for p in PARAMETERS
            if p.get("internal")
            and "Version" in p["name"]
        ]
        # HK-Konfig (Pumpen/Spannung/HK-Typ/Ext. Raumfühler etc., inkl. HKx User Betriebsart)
        hk_config_params = [
            p
            for p in PARAMETERS
            if ("bus" in p or "modultyp" in p)
            and p not in hk_process_params
            and p not in hk_version_params
            and p not in date_params
            and not p["name"].startswith("HK1 User ")
            and not p["name"].startswith("HK2 User ")
        ]
        # HK-Userparameter (Form_Heizung_Benutzer) explizit trennen, damit sie
        # in eigenen, kleinen Requests wie in der Original-WebApp abgefragt werden.
        hk_user_params = [
            p
            for p in PARAMETERS
            if p["name"].startswith("HK1 User ") or p["name"].startswith("HK2 User ")
        ]

        url = f"http://{self._host}{ENDPOINT}"

        # Check if authentication is required
        if self._username and self._password:
            auth = HTTPDigestAuth(self._username, self._password)
        else:
            auth = None

        for attempt in range(3):  # Bis zu 3 Versuche, falls die Anfrage fehlschlägt
            try:
                result = {}

                # Mehrere Requests: globale Parameter, Heizkreis-Prozesswerte,
                # Versionsparameter, Heizkreis-Konfig/User-Parameter und
                # Fachmann-/Expert-Parameter separat, analog zur WebApp.
                for params in (
                    global_params,
                    hk_process_params,
                    hk_version_params,
                    hk_config_params,
                    hk_user_params,  # eigener Block nur für HK1/HK2 User-Parameter
                    date_params,     # HK1 Holiday Temp Level + System Date/Time + DST
                    expert_params,
                ):
                    if not params:
                        continue

                    req = requests.post(
                        url,
                        auth=auth,
                        data=json.dumps(build_read_request(params)),
                        headers={'Content-Type': 'application/json'},
                        timeout=60  # Timeout auf 60 Sekunden erhöhen
                    )
                    req.raise_for_status()

                    # Prüfen, ob die Antwort gültig ist
                    if req.text.strip() == "":
                        raise WeishauptCommunicationError(
                            "Received empty response from Weishaupt WCM-COM"
                        )

                    # Prüfen, ob der Server überlastet ist (Server antwortet mit HTML)
                    if "<HTML>" in req.text.upper():
                        raise WeishauptCommunicationError(
                            "Received 'server busy' response from Weishaupt WCM-COM"
                        )

                    # Versuchen, die Antwort als JSON zu dekodieren
                    try:
                        response_json = req.json()
                    except json.JSONDecodeError as e:
                        raise WeishauptCommunicationError(
                            f"Invalid JSON response from Weishaupt WCM-COM: {e}"
                        ) from e

                    # Verarbeiten der empfangenen Daten
                    response_data = response_json.get("telegramm", [])
                    _LOGGER.debug(f"Raw response data: {response_data}")

                    for message in response_data:
                        # Erwartete Formate:
                        #  - Standard: [modultyp, bus, cmd, id, index, prot, data_low, data_high]
                        #  - Spezialfall (z.B. 3794/Device Conf): [modultyp, bus, cmd, id, index, prot, text]
                        if len(message) < 7:
                            _LOGGER.warning("Received malformed telegram from WCM-COM (len=%s): %s", len(message), message)
                            continue

                        param_id = message[3]
                        bus_id = message[1]
                        protocol_id = message[5]

                        if len(message) >= 8:
                            low_byte = message[6]
                            high_byte = message[7]
                        else:
                            # Keine getrennten Bytes vorhanden (z.B. Textwert) -> Dummy-Bytes
                            low_byte = 0
                            high_byte = 0

                        # Zuordnung des Parameters:
                        # 1. Bevorzuge HK-spezifische Einträge mit explizitem "bus" == bus_id
                        #    und passenden "modultyp" (FS/MS), damit 409/410 sauber
                        #    zwischen FS- und EM-Versionen getrennt werden.
                        # 2. Fallback: Einträge mit passendem "bus" (ohne modultyp).
                        # 3. Fallback: globaler Eintrag ohne "bus" (z.B. Kesselwerte)
                        candidates = [p for p in PARAMETERS if p["id"] == param_id]
                        param = next(
                            (
                                p
                                for p in candidates
                                if p.get("bus") == bus_id
                                and p.get("modultyp") == message[0]
                                and parameter_protocol(p) == protocol_id
                            ),
                            None,
                        )
                        if param is None:
                            param = next(
                                (
                                    p
                                    for p in candidates
                                    if p.get("bus") == bus_id
                                    and "modultyp" not in p
                                    and parameter_protocol(p) == protocol_id
                                ),
                                None,
                            )
                        if param is None:
                            param = next(
                                (
                                    p
                                    for p in candidates
                                    if "bus" not in p
                                    and parameter_protocol(p) == protocol_id
                                ),
                                None,
                            )

                        if param:
                            # Spezialfall: Device Conf (3794) liefert einen Text wie "WAP P3" im letzten Feld.
                            if param["id"] == 3794 and len(message) >= 7 and isinstance(message[6], str):
                                value = message[6]

                            elif param["type"] == "temperature":
                                raw_value = self.get_temperature(low_byte, high_byte)
                                value = raw_value

                                # Für Debugging von HK2 User-Parametern explizit loggen, was ankommt
                                if getattr(self, "advanced_logging", False) and param["name"].startswith("HK2 User"):
                                    _LOGGER.debug(
                                        "HK2 User parameter %s (id=%s, bus=%s) raw temperature=%s",
                                        param["name"],
                                        param["id"],
                                        bus_id,
                                        raw_value,
                                    )

                                value, should_warn = normalize_temperature_value(
                                    parameter_id=param["id"],
                                    parameter_name=param["name"],
                                    value=value,
                                    previous_values=self.previous_values,
                                )
                                if should_warn:
                                    _LOGGER.warning(
                                        "Unplausibler Temperaturwert für %s: %s. Nutze vorherigen Wert oder setze auf 'unavailable'.",
                                        param["name"],
                                        raw_value,
                                    )

                            elif param["type"] == "value":
                                value = self.get_value(low_byte, high_byte)
                                # Numerische Prüfung für 'value'
                                if not isinstance(value, (int, float)):
                                    _LOGGER.warning(f"Nicht-numerischer Wert erkannt: {value}. Setze auf 0.")
                                    value = 0  # Fallback auf 0 bei nicht-numerischen Werten

                            elif param["type"] == "percent":
                                value = self.get_value(low_byte, high_byte)
                                # P37/P38 (Max Power Heating/WW) kommen als x10 -> auf % skalieren
                                if param["id"] in (319, 345):
                                    value = value / 10

                            elif param["type"] == "binary":
                                value = self.get_binary(low_byte, high_byte)
                            elif param["type"] == "code":
                                value = self.get_code(low_byte, high_byte)
                            else:
                                value = low_byte + 256 * high_byte  # Fallback

                            # Speichern/Mergen der Werte
                            result[param["name"]] = value
                            self.previous_values[param["name"]] = value

                _LOGGER.debug(f"Received data: {result}")

                # Versionen für FS/EM aus den Rohwerten (High/Low) berechnen

                # Kessel (Bus 0) – nur FS-Version (EM ist bei Manuel N/V)
                kessel_fs_high = result.get("Kessel Version FS High")
                kessel_fs_low = result.get("Kessel Version FS Low")
                if kessel_fs_high is not None and kessel_fs_low is not None and kessel_fs_high != 0:
                    result["Kessel Config Version FS"] = f"{kessel_fs_high}.{kessel_fs_low}"

                # Heizkreise HK1/HK2 – FS/EM-Version pro Kreis
                for hk in (1, 2):
                    fs_high = result.get(f"HK{hk} Version FS High")
                    fs_low = result.get(f"HK{hk} Version FS Low")
                    em_high = result.get(f"HK{hk} Version EM High")
                    em_low = result.get(f"HK{hk} Version EM Low")

                    if fs_high is not None and fs_low is not None and fs_high != 0:
                        result[f"HK{hk} Config Version FS"] = f"{fs_high}.{fs_low}"

                    if em_high is not None and em_low is not None and em_high != 0:
                        result[f"HK{hk} Config Version EM"] = f"{em_high}.{em_low}"

                _LOGGER.debug(f"Received data (with versions): {result}")
                if not result:
                    raise WeishauptCommunicationError(
                        "WCM-COM returned no recognized parameter values"
                    )

                self._data = result  # Speichern Sie die aktualisierten Daten
                return  # Erfolgreiches Ende der Schleife, Daten erfolgreich abgerufen

            except requests.exceptions.HTTPError as err:
                if req.status_code == 401:
                    _LOGGER.error("Authentication failed. Please check your username and password.")
                else:
                    _LOGGER.error(f"HTTP error occurred: {err}")
            except requests.exceptions.RequestException as e:
                _LOGGER.warning(
                    "WCM-COM request attempt %s/3 failed: %s",
                    attempt + 1,
                    e,
                )
            except Exception as e:
                _LOGGER.warning(
                    "WCM-COM update attempt %s/3 failed: %s",
                    attempt + 1,
                    e,
                )

            if attempt < 2:
                time.sleep(attempt + 1)

        # Wenn alle Versuche fehlschlagen
        raise WeishauptCommunicationError(
            "Failed to fetch complete data from Weishaupt WCM-COM after 3 attempts"
        )

    def get_temperature(self, low_byte, high_byte):
        """Calculate temperature from two bytes."""
        raw_value = low_byte + 256 * high_byte
        if high_byte < 128:
            return raw_value / 10
        else:
            return (raw_value - 65536) / 10

    def write_parameter(
        self,
        parameter_id: int,
        bus: int,
        modultyp: int,
        code: int,
        protocol: int = 0,
    ) -> None:
        """Write one parameter while excluding concurrent reads and writes."""

        self.write_parameters(
            [(parameter_id, bus, modultyp, code, protocol)]
        )

    def write_parameters(
        self,
        writes: list[tuple[int, int, int, int, int]],
    ) -> None:
        """Write several parameters without allowing a poll between them."""

        with _lock:
            for parameter_id, bus, modultyp, code, protocol in writes:
                self._write_parameter_unlocked(
                    parameter_id,
                    bus,
                    modultyp,
                    code,
                    protocol,
                )

    def _write_parameter_unlocked(
        self,
        parameter_id: int,
        bus: int,
        modultyp: int,
        code: int,
        protocol: int,
    ) -> None:
        """Write one parameter; caller must hold the shared WCM-COM lock."""

        ENDPOINT = "/parameter.json"
        url = f"http://{self._host}{ENDPOINT}"

        telegram = {
            "prot": "coco",
            "telegramm": [
                build_coco_telegram(
                    module_type=modultyp,
                    bus=bus,
                    command=WRITE_COMMAND,
                    parameter_id=parameter_id,
                    protocol=protocol,
                    value=code,
                )
            ],
        }

        _LOGGER.debug("Writing parameter %s (bus=%s, modultyp=%s) with code %s", parameter_id, bus, modultyp, code)

        # Optional Auth wie im Read-Pfad
        if self._username and self._password:
            auth = HTTPDigestAuth(self._username, self._password)
        else:
            auth = None

        try:
            req = requests.post(
                url,
                auth=auth,
                data=json.dumps(telegram),
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            # A write is successful only when WCM-COM actually accepts it.
            if "<HTML>" in req.text.upper():
                raise WeishauptCommunicationError(
                    f"WCM-COM returned 'server busy' while writing parameter {parameter_id}"
                )

            req.raise_for_status()
            _LOGGER.debug("Write result: %s", req.text)
        except requests.exceptions.RequestException as err:
            raise WeishauptCommunicationError(
                f"Error writing WCM-COM parameter {parameter_id}: {err}"
            ) from err

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
            "prot": "coco",
            "telegramm": [
                [
                    param.get("destination", 10),
                    0,
                    1,
                    param["id"],
                    0,
                    0,
                    0,
                    0,
                ]
                for param in PARAMETERS
            ],
        }
        headers = "-H 'Content-Type: application/json'"
        auth = f"--digest -u {self._username}:{self._password}" if self._username and self._password else ""
        data = f"-d '{json.dumps(telegram)}'"
        return f"curl -X POST {auth} {headers} {data} {url}"
