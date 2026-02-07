"""Constants for the Weishaupt WCM-COM integration."""

from homeassistant.const import CONF_SCAN_INTERVAL

DOMAIN = 'weishaupt_wcm_com'
NAME_PREFIX = "Weishaupt "

# Standard Scan Interval in Sekunden
DEFAULT_SCAN_INTERVAL = 60

# Scan Interval Konfiguration
CONF_SCAN_INTERVAL = "scan_interval"


# Sensor Keys
OUTSIDE_TEMPERATURE_KEY = "Outside Temperature"
WARM_WATER_TEMPERATURE_KEY = "Warm Water Temperature"
FLOW_TEMPERATURE_KEY = "Flow Temperature"
FLUE_GAS_TEMPERATURE_KEY = "Flue Gas Temperature"
ERROR_CODE_KEY = "Status"

# Neue Konstanten
ROOM_TEMPERATURE_KEY = "Room Temperature"
OPERATION_MODE_KEY = "Operation Mode"
MIXED_EXTERNAL_TEMPERATURE_KEY = "Mixed External Temperature"
FLAME_KEY = "Flame"
GAS_VALVE_1_KEY = "Gas Valve 1"
GAS_VALVE_2_KEY = "Gas Valve 2"
PUMP_KEY = "Pump"
HEATING_KEY = "Heating"
WARM_WATER_KEY = "Warm Water"
OPERATION_PHASE_KEY = "Operation Phase"

# Mapping-Dictionaries
OPERATION_MODE_MAP = {
    0: "Automatik",
    1: "Reduziert",
    2: "Standby",
    3: "Manuell",
    # Fügen Sie weitere Modi entsprechend der Dokumentation hinzu
}

OPERATION_PHASE_MAP = {
    0: "Bereitschaft",
    6: "Heizen",
    8: "Warmwasser",
    #3: "Störung",
    #4: "Entlüften",
    #5: "Vorbereitung",
    #6: "Nachlauf",
    # Fügen Sie weitere Phasen hinzu
}
# Abfrageparameter und ihre Eigenschaften
# Standardmäßig wird Zieladresse 10 verwendet. Für einzelne Parameter (z.B.
# Raumtemperatur über den Raumregler) kann eine abweichende "destination"
# gesetzt werden.
PARAMETERS = [
    # Kessel / globale Prozesswerte (WTC-G Prozesswerte)
    {"id": 1,    "name": "Status",                    "type": "code"},
    {"id": 12,   "name": "Außentemperatur",           "type": "temperature"},
    {"id": 14,   "name": "Warmwassertemperatur",      "type": "temperature"},
    # Raumtemperatur wird unten pro Heizkreis (HK1/HK2) erfasst
    {"id": 81,   "name": "Flamme",                    "type": "binary"},
    {"id": 82,   "name": "Heizung",                   "type": "binary"},
    {"id": 83,   "name": "Warmwasser",                "type": "binary"},
    {"id": 325,  "name": "Kesseltemperatur",          "type": "temperature"},
    {"id": 373,  "name": "Betriebsphase",             "type": "value"},
    {"id": 466,  "name": "Pumpe",                     "type": "binary"},
    {"id": 3101, "name": "Vorlauftemperatur Zone",    "type": "temperature"},
    {"id": 2,    "name": "Wärmeanforderung",          "type": "temperature"},
    {"id": 13,   "name": "Vorlauftemperatur",         "type": "temperature"},
    {"id": 118,  "name": "Puffer Oben",               "type": "value"},
    {"id": 138,  "name": "Laststellung",              "type": "percent"},
    {"id": 1497, "name": "Gasventil 1",               "type": "binary"},
    {"id": 1498, "name": "Gasventil 2",               "type": "binary"},
    {"id": 2572, "name": "Gedämpfte Außentemperatur", "type": "temperature"},
    {"id": 3158, "name": "Schaltspielzahl Brenner",   "type": "value_1000"},
    {"id": 3159, "name": "Betriebsstunden Brenner",   "type": "hours_1000"},
    {"id": 700,  "name": "Zeit seit letzter Wartung", "type": "days"},

    # Fachmann / Experten-Parameter (global)
    {"id": 3794, "name": "Expert Device Conf",             "type": "value"},
    {"id": 376,  "name": "Expert Boiler Address",          "type": "value"},
    {"id": 3102, "name": "Expert Spec Level Heating Mode", "type": "temperature"},
    {"id": 3103, "name": "Expert Corr Outside Sensor",     "type": "temp_delta"},
    {"id": 2560, "name": "Expert Facility Frost Cont",     "type": "temperature"},
    {"id": 31,   "name": "Expert Min VL Target",           "type": "temperature"},
    {"id": 39,   "name": "Expert Max VL Target",           "type": "temperature"},
    {"id": 34,   "name": "Expert Switch Diff VL",          "type": "temperature"},
    {"id": 323,  "name": "Expert Burner Pulse Lock",       "type": "minutes"},
    {"id": 319,  "name": "Expert Max Power Heating",       "type": "percent"},
    {"id": 345,  "name": "Expert Max Power WW",            "type": "percent"},
    {"id": 384,  "name": "Expert Max Charge Time WW",      "type": "minutes"},

    # Heizkreis-Konfiguration HK1/HK2
    # Pumpen-/Spannungs- und Regelungsparameter (abgeleitet aus WTC WebApp Dumps)
    {"id": 857,   "name": "HK1 Config Pump",              "type": "value", "bus": 1, "modultyp": 12},
    {"id": 65019, "name": "HK1 Config Voltage",           "type": "value", "bus": 1, "modultyp": 12},
    {"id": 16,    "name": "HK1 Config HK Type",           "type": "value", "bus": 1, "modultyp": 6},
    {"id": 2419,  "name": "HK1 Config Regelvariante",     "type": "value", "bus": 1, "modultyp": 6},
    {"id": 321,   "name": "HK1 Config Ext Room Sensor",   "type": "value", "bus": 1, "modultyp": 6},

    {"id": 857,   "name": "HK2 Config Pump",              "type": "value", "bus": 2, "modultyp": 12},
    {"id": 65019, "name": "HK2 Config Voltage",           "type": "value", "bus": 2, "modultyp": 12},
    {"id": 16,    "name": "HK2 Config HK Type",           "type": "value", "bus": 2, "modultyp": 6},
    {"id": 2419,  "name": "HK2 Config Regelvariante",     "type": "value", "bus": 2, "modultyp": 6},
    {"id": 321,   "name": "HK2 Config Ext Room Sensor",   "type": "value", "bus": 2, "modultyp": 6},

    # Virtuelle Parameter für Versionsanzeigen (werden nicht direkt abgefragt)
    {"id": 0, "name": "HK1 Config Version FS", "type": "value", "virtual": True},
    {"id": 0, "name": "HK2 Config Version FS", "type": "value", "virtual": True},
    {"id": 0, "name": "HK1 Config Version EM", "type": "value", "virtual": True},
    {"id": 0, "name": "HK2 Config Version EM", "type": "value", "virtual": True},

    # Heizkreis-Prozesswerte HK1/HK2 (Form_Heizkreis_Prozesswerte)
    # HK1 (Buskennung 1)
    {"id": 2586, "name": "HK1 Gemischte Außentemperatur", "type": "temperature", "bus": 1, "modultyp": 6},
    {"id": 17,   "name": "HK1 Raumtemperatur",            "type": "temperature", "bus": 1, "modultyp": 6, "destination": 6},
    {"id": 15,   "name": "HK1 Vorlauftemperatur",         "type": "temperature", "bus": 1, "modultyp": 12},
    {"id": 14,   "name": "HK1 Warmwassertemperatur",      "type": "temperature", "bus": 1, "modultyp": 6},
    {"id": 1257, "name": "HK1 Zirkulationstemperatur",    "type": "temperature", "bus": 1, "modultyp": 12},
    {"id": 4,    "name": "HK1 Solltemperatur",            "type": "temperature", "bus": 1, "modultyp": 6},
    {"id": 2,    "name": "HK1 Solltemperatur System",     "type": "temperature", "bus": 1, "modultyp": 6},
    # HK2 (Buskennung 2)
    {"id": 2586, "name": "HK2 Gemischte Außentemperatur", "type": "temperature", "bus": 2, "modultyp": 6},
    {"id": 17,   "name": "HK2 Raumtemperatur",            "type": "temperature", "bus": 2, "modultyp": 6, "destination": 6},
    {"id": 15,   "name": "HK2 Vorlauftemperatur",         "type": "temperature", "bus": 2, "modultyp": 12},
    {"id": 14,   "name": "HK2 Warmwassertemperatur",      "type": "temperature", "bus": 2, "modultyp": 6},
    {"id": 1257, "name": "HK2 Zirkulationstemperatur",    "type": "temperature", "bus": 2, "modultyp": 12},
    {"id": 4,    "name": "HK2 Solltemperatur",            "type": "temperature", "bus": 2, "modultyp": 6},
    {"id": 2,    "name": "HK2 Solltemperatur System",     "type": "temperature", "bus": 2, "modultyp": 6},
    #{"id": 3793, "name": "Ölzähler", "type": "value"}
]

# HK-Konfigurations-Mappings (Enums)
HK_CONFIG_PUMP_MAP = {
    0: "Pumpe stufig",
}

HK_CONFIG_VOLTAGE_MAP = {
    2: "Spannung: Auto Aus",
}

HK_CONFIG_HK_TYPE_MAP = {
    2: "HK-Typ: int. Raumfühler",
}

HK_CONFIG_REGELVARIANTE_MAP = {
    1: "Regelvariante: Fußbodenheizung",
}

HK_CONFIG_EXT_ROOM_SENSOR_MAP = {
    2: "Externer Raumfühler: Witterungs-/Raumführung",
}

ERROR_CODE_MAP = {
    0: "normal",
    11: "F11: Temperatur am Vorlauffühler > 105 °C",
    12: "W12: Temperatur am Vorlauffühler > 95 °C",
    13: "F13: Abgastemperatur zu hoch",
    14: "W14: Vorlauftemperatur steigt zu schnell an",
    15: "F15/W15: Differenz Vorlauf- und Abgastemperatur zu groß - (Nach 30 Warnungen verriegelt die Anlage mit F15)",
    16: "W16: Abgastemperatur zu hoch",
    21: "F21: Keine Flammenbildung beim Brennerstart",
    22: "W22: Flammenausfall während des Betriebs",
    23: "F23: Flammenvortäuschung",
    24: "F24: Eingang H2 ist geschlossen, Parameter 17 = 3",
    30: "F30: Vorlauffühler defekt",
    31: "F31: Abgasfühler defekt",
    33: "W33: Außenfühler defekt",
    34: "W34: Warmwasserfühler defekt",
    37: "W37: Wasserströmungssensor defekt",
    38: "F38: Pufferfühler defekt",
    39: "F39: Pufferfühler/Weichenfühler defekt",
    41: "F41: Relaiskontrolle Gasventile",
    42: "W42: Kein Steuersignal Umwälzpumpe",
    43: "F43: Gebläsedrehzahl wird nicht erreicht",
    44: "F44: Gebläsestillstand fehlerhaft",
    51: "F51: Datensatz-Fehler Kessel",
    52: "F52: Datensatz-Fehler Brenner",
    53: "F53: Spannungsversorgung außerhalb Toleranz",
    54: "F54: Elektronikfehler",
    55: "F55: Netzfrequenz außerhalb Toleranz",
    56: "F56: Ionisationsmessung fehlerhaft",
    61: "F61: Ionisationssignal weicht vom Sollwert ab",
    62: "F62: Stellsignal des Gasstellglieds außerhalb Toleranz",
    64: "F64: SCOT®-Basiswert außerhalb vorgegebener Grenzen",
    65: "F65: SCOT®-Basiswert weicht zu stark vom Vorgängerwert ab",
    66: "F66: Kalibrierung konnte nicht durchgeführt werden",
    67: "F67: SCOT®-Basiswert fehlerhaft gespeichert",
    80: "W80: Kommunikation zum Kaskadenmanager fehlerhaft",
    81: "W81: Kommunikation zur WCM-FS#1 fehlerhaft",
    82: "W82: Kommunikation zu EM#2 oder WCM-FS#2 fehlerhaft",
    83: "W83: Kommunikation zu EM#3 oder WCM-FS#3 fehlerhaft",
    84: "W84: Kommunikation zu EM#4 oder WCM-FS#4 fehlerhaft",
    85: "W85: Kommunikation zu EM#5 oder WCM-FS#5 fehlerhaft",
    86: "W86: Kommunikation zu EM#6 oder WCM-FS#6 fehlerhaft",
    87: "W87: Kommunikation zu EM#7 oder WCM-FS#7 fehlerhaft",
    88: "W88: Kommunikation zu EM#8 oder WCM-FS#8 fehlerhaft",
    # Weitere Codes hinzufügen, falls vorhanden
}
# Warncode-Mapping
WARNING_CODE_MAP = {
    12: "W12: Temperatur am Vorlauffühler > 95 °C",
    14: "W14: Vorlauftemperatur steigt zu schnell an",
    15: "W15: Differenz Vorlauf- und Abgastemperatur zu groß",
    16: "W16: Abgastemperatur zu hoch",
    22: "W22: Flammenausfall während des Betriebs",
    33: "W33: Außenfühler defekt",
    34: "W34: Warmwasserfühler defekt",
    37: "W37: Wasserströmungssensor defekt",
    42: "W42: Kein Steuersignal Umwälzpumpe",
    80: "W80: Kommunikation zum Kaskadenmanager fehlerhaft",
    81: "W81: Kommunikation zur WCM-FS#1 fehlerhaft",
    82: "W82: Kommunikation zu EM#2 oder WCM-FS#2 fehlerhaft",
    83: "W83: Kommunikation zu EM#3 oder WCM-FS#3 fehlerhaft",
    84: "W84: Kommunikation zu EM#4 oder WCM-FS#4 fehlerhaft",
    85: "W85: Kommunikation zu EM#5 oder WCM-FS#5 fehlerhaft",
    86: "W86: Kommunikation zu EM#6 oder WCM-FS#6 fehlerhaft",
    87: "W87: Kommunikation zu EM#7 oder WCM-FS#7 fehlerhaft",
    88: "W88: Kommunikation zu EM#8 oder WCM-FS#8 fehlerhaft",
    # Weitere Warncodes hinzufügen, falls vorhanden
}
