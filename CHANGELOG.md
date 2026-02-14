# Changelog

## 1.2.6b18

- Fix: Make `HK1/HK2 Expert Ein Opti MAX` sensors report minutes (0–240, step 15) consistent with the number entities.
- Fix: Align `HK1/HK2 Expert Frostheizgrenze` sensors with the UI/number behavior by treating raw value `10` as "not set" (sensor becomes `unavailable`).

## 1.2.6b17

- Fix: Add missing `datetime` import for System Date/Time validation logic.

## 1.2.6b16

- Chore: Version bump and internal cleanup towards 1.2.6.
