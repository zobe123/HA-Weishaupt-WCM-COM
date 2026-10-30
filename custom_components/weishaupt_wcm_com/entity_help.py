"""Localized, evidence-backed context help for public WCM entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class HelpDefinition:
    """Documentation for one entity or repeated entity family."""

    description_de: str
    description_en: str
    menu_parameter: str | None = None
    notice_de: str | None = None
    notice_en: str | None = None


def _help(
    description_de: str,
    description_en: str,
    menu_parameter: str | None = None,
    notice_de: str | None = None,
    notice_en: str | None = None,
) -> HelpDefinition:
    return HelpDefinition(
        description_de,
        description_en,
        menu_parameter,
        notice_de,
        notice_en,
    )


# Names without a circuit prefix. Descriptions are based on the original
# WCM-COM WebUI and the Weishaupt WTC/WCM-FS manuals. Factory defaults are not
# included because they vary by appliance, hydraulic configuration and profile.
_EXACT_HELP: dict[str, HelpDefinition] = {
    "Status": _help("Aktueller WTC-Fehler- oder Warnstatus.", "Current WTC fault or warning status."),
    "Außentemperatur": _help("Vom Außenfühler gemessene Temperatur.", "Temperature measured by the outdoor sensor."),
    "Warmwassertemperatur": _help("Aktuelle Temperatur des Warmwasserspeichers.", "Current domestic-hot-water storage temperature."),
    "Flamme": _help("Meldet, ob der Brenner eine Flamme erkannt hat.", "Indicates whether the burner has detected a flame."),
    "Heizung": _help("Meldet eine aktive Wärmeerzeugung für den Heizbetrieb.", "Indicates active heat generation for space heating."),
    "Warmwasser": _help("Meldet eine aktive Warmwasserbereitung.", "Indicates active domestic-hot-water heating."),
    "Kesseltemperatur": _help("Aktuelle Temperatur im Wärmeerzeuger.", "Current heat-generator temperature."),
    "Betriebsphase": _help("Aktuelle Ablaufphase des Brenners; zeitabhängige Zwischenwerte werden kontextbezogen dargestellt.", "Current burner sequence phase; time-dependent intermediate values are displayed in context."),
    "Pumpe": _help("Betriebszustand der internen Umwälzpumpe.", "Operating state of the internal circulation pump."),
    "Vorlauftemperatur Zone": _help("Aktuelle Vorlauftemperatur der vom WTC versorgten Zone.", "Current flow temperature of the zone supplied by the WTC."),
    "Wärmeanforderung": _help("Vom Regelsystem angeforderte Wärmeerzeuger-Solltemperatur.", "Heat-generator target temperature requested by the control system."),
    "Vorlauftemperatur": _help("Aktuelle Vorlauftemperatur des Wärmeerzeugers.", "Current heat-generator flow temperature."),
    "Puffer Oben": _help("Temperatur am oberen Pufferfühler, sofern vorhanden.", "Temperature at the upper buffer sensor, when installed."),
    "Laststellung": _help("Aktuelle Brennerleistung bzw. Leistungsstufe.", "Current burner output or firing stage."),
    "Gasventil 1": _help("Schaltzustand des ersten Gasventils.", "Switching state of the first gas valve."),
    "Gasventil 2": _help("Schaltzustand des zweiten Gasventils.", "Switching state of the second gas valve."),
    "Magnetventil 1": _help("Schaltzustand des ersten Öl-Magnetventils.", "Switching state of the first oil solenoid valve."),
    "Magnetventil 2": _help("Schaltzustand des zweiten Öl-Magnetventils.", "Switching state of the second oil solenoid valve."),
    "Gedämpfte Außentemperatur": _help("Zeitlich gedämpfte Außentemperatur für Regelungsentscheidungen.", "Time-filtered outdoor temperature used for control decisions."),
    "Schaltspielzahl Brenner": _help("Vom Wärmeerzeuger gezählte Brennerstarts.", "Burner starts counted by the heat generator."),
    "Betriebsstunden Brenner": _help("Kumulierte Laufzeit des Brenners.", "Accumulated burner operating time."),
    "Ölzähler": _help("Vom WTC-OB gemeldeter kumulierter Ölverbrauch.", "Accumulated oil consumption reported by the WTC-OB."),
    "Zeit seit letzter Wartung": _help("Brennerlaufzeit seit dem letzten Wartungsreset.", "Burner operating time since the last maintenance reset."),
    "Expert Device Conf": _help("Vom WTC erkannte Gerätekonfiguration.", "Appliance configuration detected by the WTC.", "P10"),
    "Expert Boiler Address": _help("eBUS-Adresse des Wärmeerzeugers.", "eBUS address of the heat generator.", "P12"),
    "Expert Spec Level Heating Mode": _help("Zusätzliches Temperaturniveau für den Heizbetrieb.", "Additional temperature level for heating mode.", "P18"),
    "Expert Corr Outside Sensor": _help("Korrekturwert für den gemessenen Außenfühler.", "Correction applied to the measured outdoor temperature.", "P20"),
    "Expert Facility Frost Cont": _help("Temperaturgrenze für den Anlagenfrostschutz.", "Temperature threshold for system frost protection.", "P23"),
    "Expert Min VL Target": _help("Untere Begrenzung der Vorlauf-Solltemperatur.", "Lower limit for the target flow temperature.", "P30"),
    "Expert Max VL Target": _help("Obere Begrenzung der Vorlauf-Solltemperatur.", "Upper limit for the target flow temperature.", "P31"),
    "Expert Switch Diff VL": _help("Schaltdifferenz der Vorlaufregelung.", "Switching differential of the flow-temperature control.", "P32"),
    "Expert Burner Pulse Lock": _help("Mindestpause zwischen zwei Brennerstarts.", "Minimum pause between two burner starts.", "P34"),
    "Expert Max Power Heating": _help("Maximale Brennerleistung im Heizbetrieb.", "Maximum burner output in heating mode.", "P37"),
    "Expert Max Power Heating OB": _help("Maximale Brennerleistung des WTC-OB im Heizbetrieb.", "Maximum WTC-OB burner output in heating mode.", "P37"),
    "Expert Max Power WW": _help("Maximale Brennerleistung bei der Warmwasserbereitung.", "Maximum burner output during domestic-hot-water heating.", "P38"),
    "Expert Max Charge Time WW": _help("Maximale Dauer einer Warmwasserladung.", "Maximum duration of one domestic-hot-water heating cycle.", "P52"),
    "System Date": _help("Aus den WCM-Datumsfeldern zusammengesetztes Systemdatum.", "System date assembled from the WCM date fields."),
    "System Time": _help("Aus den WCM-Zeitfeldern zusammengesetzte Systemzeit.", "System time assembled from the WCM time fields."),
    "DST Start": _help("Im WCM gespeicherter Beginn der Sommerzeit.", "Daylight-saving start stored in the WCM."),
    "DST End": _help("Im WCM gespeichertes Ende der Sommerzeit.", "Daylight-saving end stored in the WCM."),
}


# Repeated suffixes cover WTC-HK1/FS1 and both extension circuits without
# duplicating text. Menu numbers follow the original WCM-COM user interface.
_SUFFIX_HELP: dict[str, HelpDefinition] = {
    "Config Pump": _help("Konfiguration des Heizkreis-Pumpenausgangs.", "Heating-circuit pump-output configuration."),
    "Config Voltage": _help("Schaltzustand bzw. Ansteuerung des Pumpenausgangs.", "Switching state or control mode of the pump output."),
    "Config HK Type": _help("Legt den angeschlossenen Heizkreistyp fest.", "Defines the connected heating-circuit type.", "P316"),
    "Config Regelvariante": _help("Legt fest, nach welchen Führungsgrößen der Heizkreis geregelt wird.", "Defines which reference values control the heating circuit.", "P318"),
    "Config Ext Room Sensor": _help("Legt fest, welcher Raumfühler für den Heizkreis verwendet wird.", "Defines which room sensor is used for the heating circuit.", "P414"),
    "Config Version FS": _help("Firmwareversion der Fernbedienstation WCM-FS.", "Firmware version of the WCM-FS remote control."),
    "Config Version EM": _help("Firmwareversion des Erweiterungsmoduls WCM-EM.", "Firmware version of the WCM-EM extension module."),
    "Gemischte Außentemperatur": _help("Vom Regler aus aktueller und gedämpfter Außentemperatur gebildeter Mischwert.", "Outdoor-temperature value combined by the controller from current and filtered readings."),
    "Raumtemperatur": _help("Vom zugeordneten Raumfühler gemessene Temperatur.", "Temperature measured by the assigned room sensor."),
    "Vorlauftemperatur": _help("Am Heizkreis gemessene Vorlauftemperatur.", "Flow temperature measured in the heating circuit."),
    "Warmwassertemperatur": _help("Vom Heizkreismodul gemeldete Warmwassertemperatur.", "Domestic-hot-water temperature reported by the circuit module."),
    "Zirkulationstemperatur": _help("Temperatur am Zirkulationsfühler, sofern vorhanden.", "Temperature at the circulation sensor, when installed."),
    "Solltemperatur System": _help("Vom Gesamtsystem für diesen Heizkreis berechnete Solltemperatur.", "Target temperature calculated by the overall system for this circuit."),
    "Solltemperatur": _help("Aktuelle Solltemperatur des Heizkreises.", "Current target temperature of the heating circuit."),
    "User Betriebsart": _help("Gewählte Betriebsart bzw. das aktive Zeitprogramm.", "Selected operating mode or active time program.", "111/131"),
    "User Normal Raumtemperatur": _help("Raumtemperatur-Sollwert für den Normalbetrieb.", "Room-temperature target for normal operation.", "112"),
    "User Absenk Raumtemperatur": _help("Raumtemperatur-Sollwert für den Absenkbetrieb.", "Room-temperature target for reduced operation.", "113"),
    "User Normal VL Soll": _help("Vorlauf-Solltemperatur für den Normalbetrieb bei Konstantvorlauf.", "Flow-temperature target for normal operation with constant-flow control.", "115"),
    "User Absenk VL Soll": _help("Vorlauf-Solltemperatur für den Absenkbetrieb bei Konstantvorlauf.", "Flow-temperature target for reduced operation with constant-flow control.", "116"),
    "User Steilheit": _help("Steilheit der Heizkennlinie; der sinnvolle Bereich hängt vom Heizkreistyp ab.", "Heating-curve slope; the useful range depends on the heating-circuit type.", "117"),
    "User Raumfrosttemperatur": _help("Raumbezogener Sollwert für den Frostschutzbetrieb; er wirkt auf die Vorlauftemperatur.", "Room-related target for frost-protection mode; it affects the flow temperature.", "118"),
    "User SoWi Umschaltung": _help("Außentemperaturgrenze für die automatische Sommer-/Winterumschaltung.", "Outdoor-temperature threshold for automatic summer/winter changeover.", "119"),
    "User Normal WW Soll": _help("Warmwasser-Solltemperatur für den Normalbetrieb.", "Domestic-hot-water target for normal operation.", "132"),
    "User Absenk WW Soll": _help("Warmwasser-Solltemperatur für den Absenkbetrieb.", "Domestic-hot-water target for reduced operation.", "133"),
    "User Vorverlegung": _help("Zeitliche Vorverlegung des Erweiterungsheizkreises gegenüber dem führenden Heizkreis.", "Time advance of the extension circuit relative to the leading heating circuit.", "161"),
    "Expert Reduziertbetrieb": _help("Verhalten des Heizkreises während der Absenkphase.", "Heating-circuit behavior during reduced operation.", "P501"),
    "Expert Frostheizgrenze": _help("Außentemperaturgrenze für den Frostschutz-Heizbetrieb.", "Outdoor-temperature threshold for frost-protection heating.", "P502"),
    "Expert Ein Opti MAX": _help("Maximale Vorverlegung des Heizbeginns durch die Einschaltoptimierung.", "Maximum advance of heating start by switch-on optimization.", "P503", "Das WCM überträgt 15-Minuten-Blöcke; angezeigt werden echte Minuten.", "The WCM transmits 15-minute blocks; actual minutes are displayed."),
    "Expert Ein Opti IST": _help("Aktuell von der Einschaltoptimierung berechnete Vorverlegung.", "Current heating-start advance calculated by switch-on optimization.", "P503"),
    "Expert Raumthermostat": _help("Aktiviert bzw. parametriert den Raumthermostat-Einfluss.", "Enables or configures room-thermostat influence.", "P505"),
    "Expert Max Charge Time WW": _help("Maximale Dauer einer Warmwasserladung dieses Heizkreismoduls.", "Maximum domestic-hot-water heating duration for this circuit module.", "P604"),
    "Holiday Start": _help("Beginn des im WCM gespeicherten Urlaubszeitraums.", "Start of the holiday period stored in the WCM.", "141"),
    "Holiday End": _help("Ende des im WCM gespeicherten Urlaubszeitraums.", "End of the holiday period stored in the WCM.", "141"),
    "Urlaubstemperaturniveau": _help("Temperaturniveau während des Urlaubszeitraums.", "Temperature level used during the holiday period.", "142"),
}


def _definition_for(name: str) -> HelpDefinition | None:
    """Return the narrowest help definition for an entity name."""

    if definition := _EXACT_HELP.get(name):
        return definition
    for suffix in sorted(_SUFFIX_HELP, key=len, reverse=True):
        if name.endswith(suffix):
            return _SUFFIX_HELP[suffix]
    return None


def coordinator_language(coordinator: Any) -> str:
    """Return the Home Assistant core language without requiring it in tests."""

    config = getattr(getattr(coordinator, "hass", None), "config", None)
    language = getattr(config, "language", "en")
    return language if isinstance(language, str) else "en"


def entity_help_attributes(
    name: str,
    *,
    language: str,
    value_range: str | None = None,
    parameter: Mapping[str, Any] | None = None,
) -> dict[str, str | int]:
    """Build stable state attributes for a documented public entity."""

    definition = _definition_for(name)
    if definition is None:
        return {}

    german = language.lower().startswith("de")
    description = definition.description_de if german else definition.description_en
    attributes: dict[str, str | int] = {"description": description}

    if definition.menu_parameter:
        attributes["parameter"] = definition.menu_parameter

    if parameter is not None:
        parameter_id = parameter.get("id")
        if isinstance(parameter_id, int) and parameter_id > 0:
            attributes["wcm_parameter"] = parameter_id
            if "parameter" not in attributes:
                attributes["parameter"] = f"WCM ID {parameter_id}"
        if "bus" in parameter:
            attributes["wcm_bus"] = int(parameter["bus"])
        module = parameter.get("modultyp", parameter.get("destination"))
        if module is not None:
            attributes["wcm_module"] = int(module)
        if parameter.get("virtual"):
            attributes["derived_value"] = "ja" if german else "yes"

    if value_range:
        attributes["value_range"] = value_range

    notice = definition.notice_de if german else definition.notice_en
    if notice:
        attributes["notice"] = notice
    attributes["documentation_basis"] = (
        "Weishaupt-Handbuch / originale WCM-COM-WebUI"
        if german
        else "Weishaupt manual / original WCM-COM WebUI"
    )
    return attributes
