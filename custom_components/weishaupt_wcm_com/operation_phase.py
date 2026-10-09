"""Decode WTC burner operation phase values."""

OPERATION_PHASE_MAP = {
    0: "Brenner aus",
    1: "Ruhestandskontrolle Gebläse",
    2: "Vorspüldrehzahl erreichen",
    3: "Countdown der Vorspülzeit",
    4: "Zünddrehzahl erreichen",
    5: "Flammenbildungszeit",
    6: "Brenner in Betrieb, Regelung aktiv",
    7: "Gasventilkontrolle V1",
    8: "Gasventilkontrolle V2",
    9: "Nachspüldrehzahl erreichen und Nachspülen",
}


def format_operation_phase(value: object, *, flame_on: bool = False) -> str:
    """Return the documented WTC burner phase for an I10/parameter 373 value.

    During phase 3 the controller exposes the remaining pre-purge time instead
    of the phase number (``Tv ... 0``). During phase 5 it exposes flame-formation
    time in tenths of a second (``0 ... Tz``). The flame signal distinguishes
    these dynamic displays for the values observed on this installation.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return f"Unbekannte Betriebsphase ({value})"

    mapped = OPERATION_PHASE_MAP.get(value)
    if mapped is not None:
        return mapped

    if 10 <= value <= 60:
        if flame_on:
            return f"Flammenbildungszeit {value / 10:.1f} s"
        return f"Vorspülzeit – noch {value} s"

    return f"Unbekannte Betriebsphase ({value})"
