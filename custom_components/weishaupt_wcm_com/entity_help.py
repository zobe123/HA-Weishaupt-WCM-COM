"""Short, evidence-backed help text for configurable WCM entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HelpDefinition:
    """Localized help for one original WCM menu parameter."""

    menu_parameter: str
    description_de: str
    description_en: str
    notice_de: str | None = None
    notice_en: str | None = None


_GLOBAL_HELP: dict[str, HelpDefinition] = {
    "Expert Spec Level Heating Mode": HelpDefinition(
        "P18",
        "Sonderniveau für den Heizbetrieb.",
        "Special temperature level for heating mode.",
    ),
    "Expert Corr Outside Sensor": HelpDefinition(
        "P20",
        "Korrekturwert für den gemessenen Außentemperaturfühler.",
        "Correction applied to the measured outdoor temperature.",
    ),
    "Expert Min VL Target": HelpDefinition(
        "P30",
        "Untere Begrenzung der Vorlauf-Solltemperatur.",
        "Lower limit for the target flow temperature.",
    ),
    "Expert Max VL Target": HelpDefinition(
        "P31",
        "Obere Begrenzung der Vorlauf-Solltemperatur.",
        "Upper limit for the target flow temperature.",
    ),
    "Expert Switch Diff VL": HelpDefinition(
        "P32",
        "Schaltdifferenz der Vorlaufregelung.",
        "Switching differential of the flow-temperature control.",
    ),
    "Expert Burner Pulse Lock": HelpDefinition(
        "P34",
        "Mindestpause zwischen zwei Brennerstarts.",
        "Minimum pause between two burner starts.",
    ),
    "Expert Max Power Heating": HelpDefinition(
        "P37",
        "Maximale Brennerleistung im Heizbetrieb.",
        "Maximum burner output in heating mode.",
    ),
    "Expert Max Power WW": HelpDefinition(
        "P38",
        "Maximale Brennerleistung bei der Warmwasserbereitung.",
        "Maximum burner output during domestic-hot-water heating.",
    ),
    "Expert Max Charge Time WW": HelpDefinition(
        "P52",
        "Maximale Dauer einer Warmwasserladung.",
        "Maximum duration of one domestic-hot-water heating cycle.",
    ),
}


_SUFFIX_HELP: dict[str, HelpDefinition] = {
    "Config HK Type": HelpDefinition(
        "P316",
        "Legt den angeschlossenen Heizkreistyp fest.",
        "Defines the connected heating-circuit type.",
    ),
    "Config Regelvariante": HelpDefinition(
        "P318",
        "Legt fest, nach welchen Führungsgrößen der Heizkreis geregelt wird.",
        "Defines which reference values control the heating circuit.",
    ),
    "Config Ext Room Sensor": HelpDefinition(
        "P414",
        "Legt fest, welcher Raumfühler für den Heizkreis verwendet wird.",
        "Defines which room sensor is used for the heating circuit.",
    ),
    "Expert Reduziertbetrieb": HelpDefinition(
        "P501",
        "Verhalten des Heizkreises während der Absenkphase.",
        "Heating-circuit behavior during reduced operation.",
    ),
    "Expert Frostheizgrenze": HelpDefinition(
        "P502",
        "Außentemperaturgrenze für den Frostschutz-Heizbetrieb.",
        "Outdoor-temperature threshold for frost-protection heating.",
    ),
    "Expert Ein Opti MAX": HelpDefinition(
        "P503",
        "Maximale Vorverlegung des Heizbeginns durch die Einschaltoptimierung.",
        "Maximum advance of heating start by switch-on optimization.",
        "Das WCM überträgt 15-Minuten-Blöcke; angezeigt werden echte Minuten.",
        "The WCM transmits 15-minute blocks; actual minutes are displayed.",
    ),
    "Expert Raumthermostat": HelpDefinition(
        "P505",
        "Aktiviert oder deaktiviert den Raumthermostat-Einfluss.",
        "Enables or disables room-thermostat influence.",
    ),
    "Expert Max Charge Time WW": HelpDefinition(
        "P604",
        "Maximale Dauer einer Warmwasserladung dieses Heizkreismoduls.",
        "Maximum domestic-hot-water heating duration for this circuit module.",
    ),
}


def _definition_for(name: str) -> HelpDefinition | None:
    """Return the narrowest help definition for an entity name."""

    if definition := _GLOBAL_HELP.get(name):
        return definition
    return next(
        (
            definition
            for suffix, definition in _SUFFIX_HELP.items()
            if name.endswith(suffix)
        ),
        None,
    )


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
) -> dict[str, str]:
    """Build stable state attributes for a supported configurable entity."""

    definition = _definition_for(name)
    if definition is None:
        return {}

    german = language.lower().startswith("de")
    attributes = {
        "parameter": definition.menu_parameter,
        "description": (
            definition.description_de if german else definition.description_en
        ),
    }
    if value_range:
        attributes["value_range"] = value_range

    notice = definition.notice_de if german else definition.notice_en
    if notice:
        attributes["notice"] = notice
    return attributes
