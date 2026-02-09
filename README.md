# HA-Weishaupt-WCM-COM Home Integration

[![GitHub release](https://img.shields.io/github/release/zobe123/HA-Weishaupt-WCM-COM.svg)](https://github.com/zobe123/HA-Weishaupt-WCM-COM/releases)

## Overview

This Home Assistant integration allows communication with the Weishaupt WCM-COM heating control system.  
It reads important parameters from your boiler and heating circuits and exposes them as sensors in Home Assistant so you can monitor and optimize your heating system.

## Features

- Query important operational parameters such as:
  - Outside temperature
  - Flow temperature (boiler and zones)
  - Hot water temperature
  - Pump and valve status
  - Burner runtime, cycle count and error / warning codes
- Display values in Home Assistant dashboards (history graphs, status indicators, diagnostics).
- Map error and warning codes to human readable text for easier diagnosis.
- Expose **expert parameters** from the WTC expert menu (P10/P12/P18/…/P52) as diagnostic sensors (depending on your installation).

## Requirements

- Home Assistant Core
- Weishaupt WCM-COM control unit reachable in your local network
- Network connection to the Weishaupt WCM-COM (via LAN)
- Python 3.8 or higher

## Installation

### 1. HACS (recommended – custom repository)

Until this integration is part of the official HACS default store, you can install it as a custom repository:

1. In Home Assistant, go to **HACS → Integrations**.
2. Click the three dots in the top right → **Custom repositories**.
3. Add:

   - **Repository**: `https://github.com/zobe123/HA-Weishaupt-WCM-COM`  
   - **Category**: `Integration`

4. After adding the custom repository, search for **Weishaupt WCM-COM** in HACS and install it.
5. Restart Home Assistant.

### 2. Manual installation

1. Clone this repository into your `custom_components` folder:

   ```bash
   git clone https://github.com/zobe123/HA-Weishaupt-WCM-COM \
     ~/.homeassistant/custom_components/weishaupt_wcm_com
   ```

2. Restart Home Assistant.

## Configuration

1. Open Home Assistant and go to **Settings → Devices & Services**.
2. Click **Add Integration** and search for **Weishaupt WCM-COM**.
3. Enter:
   - the IP address of your WCM-COM,
   - optional username and password (if configured on the device).
4. Confirm to create the integration.

You can later change IP, username, password and the scan interval via the integration’s **Reconfigure** (wrench) options flow.

## Parameters and Entities

The integration queries various parameters from the WCM-COM interface and exposes them as sensors, for example:

- `Außentemperatur` – outside temperature
- `Vorlauftemperatur` – boiler flow temperature
- `Warmwassertemperatur` – hot water temperature
- `Pumpe`, `Flamme`, `Heizung`, `Warmwasser` – on/off status
- `Status` – error/warning code with mapped description
- `HK1/HK2 …` – heating circuit 1/2 process values
- **Expert …** – diagnostic values from the WTC expert menu (P10/P12/P18/P20/P23/P30/P31/P32/P34/P37/P38/P52)

Expert sensors are marked as diagnostic entities in Home Assistant and may be `unavailable` if your installation does not expose the corresponding value.

## Usage notes

- Ensure that your Weishaupt WCM-COM device is reachable on the network.
- The WCM-COM server can handle only a limited number of simultaneous requests. Avoid very short polling intervals to prevent overloading the device.
- If you see a "server busy" HTML response, increase the scan interval.
- Some values (especially expert or circulation temperatures) may be temporarily `unavailable` if the controller reports invalid values (e.g. −100 °C) or does not support the parameter in your configuration.

### Read-only vs. write mode

By default the integration runs in a **read-only** mode:

- All process and expert values are read from the WCM-COM and exposed as entities.
- Configuration entities (expert sliders, HK1/HK2 config selects) are visible but writes are blocked.

If you really want to change configuration parameters from Home Assistant, you must explicitly enable writes in the integration options:

1. Go to **Settings → Devices & Services → Weishaupt WCM-COM → Configure**.
2. Enable **"Allow writes to WCM-COM (expert mode)"**.

When this flag is disabled again, all further write attempts from HA are rejected and logged, while reading continues as usual.

## Debugging

To enable detailed logging for debugging, add the following to your `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.weishaupt_wcm_com: debug
```

## Contributing

Bug reports and pull requests are welcome.  
Please use the [issue tracker](https://github.com/zobe123/HA-Weishaupt-WCM-COM/issues) for problems and feature requests.

## License

This project is licensed under the MIT License.  
See the [LICENSE](LICENSE) file for details.

## Acknowledgments

This project was originally based on the work of [schmiegelt/HA-Weishaupt-WCM-COM](https://github.com/schmiegelt/HA-Weishaupt-WCM-COM).  
Thanks for the inspiration and groundwork.
