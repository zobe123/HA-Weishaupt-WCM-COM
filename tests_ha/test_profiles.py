"""Behavior tests for WTC boiler profiles."""

from custom_components.weishaupt_wcm_com.const import (
    BOILER_PROFILE_WTC_G,
    BOILER_PROFILE_WTC_OB,
    detected_profile,
    parameters_for_profile,
)
from custom_components.weishaupt_wcm_com.weishaupt_api import (
    combine_wtc_ob_counters,
)
from custom_components.weishaupt_wcm_com.sensor import scale_profile_value


def test_read_only_probe_requires_an_unambiguous_profile() -> None:
    gas = {
        "WTC-G Burner Cycles Detection": 1,
        "WTC-G Burner Hours Detection": 2,
        # These WTC-OB IDs were observed on a real WTC-G and must not count.
        "WTC-OB Counter Low Detection": 3,
    }
    assert detected_profile(gas) == BOILER_PROFILE_WTC_G
    assert (
        detected_profile(
            {
                "WTC-OB Burner Output Detection": 42,
                "WTC-OB Burner Hours Low Detection": 2,
                "WTC-OB Burner Hours High Detection": 3,
            }
        )
        == BOILER_PROFILE_WTC_OB
    )
    assert detected_profile({}) is None
    assert (
        detected_profile(
            {
                **gas,
                "WTC-OB Burner Output Detection": 42,
                "WTC-OB Burner Hours Low Detection": 2,
                "WTC-OB Burner Hours High Detection": 3,
            }
        )
        is None
    )


def test_profile_parameter_sets_do_not_cross_poll() -> None:
    gas_ids = {parameter["id"] for parameter in parameters_for_profile("wtc_g")}
    oil_ids = {parameter["id"] for parameter in parameters_for_profile("wtc_ob")}

    assert 3158 in gas_ids and 3197 not in gas_ids
    assert 3197 in oil_ids and 3158 not in oil_ids


def test_oil_high_low_words_match_original_webui() -> None:
    data = {
        "WTC-OB Schaltspiele High": 12,
        "WTC-OB Schaltspiele Low": 345,
        "WTC-OB Betriebsstunden High": 6,
        "WTC-OB Betriebsstunden Low": 789,
        "WTC-OB Ölzähler High": 3,
        "WTC-OB Ölzähler Low": 210,
    }

    combine_wtc_ob_counters(data)

    assert data["Schaltspielzahl Brenner"] == 12345
    assert data["Betriebsstunden Brenner"] == 6789
    assert data["Ölzähler"] == 3210


def test_webui_profile_scaling() -> None:
    assert scale_profile_value("hours_100", 123) == 12300
    assert scale_profile_value("hours_10", 12) == 120
    assert scale_profile_value("power_tenths", 456) == 45.6
