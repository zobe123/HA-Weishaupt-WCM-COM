# HA-Weishaupt-WCM-COM Integration

[![GitHub release](https://img.shields.io/github/release/zobe123/HA-Weishaupt-WCM-COM.svg)](https://github.com/zobe123/HA-Weishaupt-WCM-COM/releases)

## Overview

This Home Assistant integration allows communication with the Weishaupt WCM-COM heating control system. With this integration, you can read important parameters of your heating system and visualize them in Home Assistant, enabling you to monitor and optimize the operation of your heating system.

## Features

- Query important operational parameters such as:
  - Outside temperature
  - Flow temperature
  - Hot water temperature
  - Operating status of pumps and valves
  - Burner runtime and error codes
- Display the values via Home Assistant dashboards (e.g., historical graphs for temperatures and status indicators).
- Integration of error and warning codes with plain text descriptions for easier diagnosis.

## Requirements

- Home Assistant Core
- Weishaupt WCM-COM control unit accessible on the local network
- Network connection to the Weishaupt WCM-COM (via LAN)
- Python 3.8 or higher

## Installation

### Manual Installation

1. Clone the repository into your custom components folder:
   ```bash
   git clone https://github.com/zobe123/HA-Weishaupt-WCM-COM ~/.homeassistant/custom_components/weishaupt_wcm_com
2. Restart Home Assistant.

### HACS Installation (TODO)
Adding support for HACS installation is planned for a future update.

## Configuration

1. Open Home Assistant and go to **Settings** > **Integrations**.
2. Click on **Add Integration** and search for **Weishaupt WCM-COM**.
3. Enter the IP address of the Weishaupt WCM-COM, along with an optional username and password.
4. Save the configuration.

## Parameters and Entities

The integration queries various parameters from the WCM-COM interface. The collected parameters are displayed as sensor entities in Home Assistant. Here are some of the available entities:

- **sensor.weishaupt_outside_temperature**: Outside temperature
- **sensor.weishaupt_flow_temperature**: Flow temperature
- **sensor.weishaupt_warm_water_temperature**: Hot water temperature
- **sensor.weishaupt_burner_state**: Burner status (On/Off)
- **sensor.weishaupt_error_code**: Heating system error code (with plain text description)

## Usage Notes

- Ensure that your Weishaupt WCM-COM device is reachable on the network.
- The WCM-COM server can handle only a limited number of simultaneous requests. Avoid short polling intervals to prevent overloading the server.
- If you see the "Server is busy" error, consider increasing the polling interval.

## Known Issues

- If there are too many simultaneous requests, the "Server is busy" message may appear. Increasing the polling interval can help in this case.
- Some values may occasionally be unavailable if the server does not respond.

## Debugging

To enable detailed logging for debugging, add the following to your `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.weishaupt_wcm_com: debug

## Contributing

Contributions to this project are welcome. Please create a pull request or report issues in the [Issue Tracker](https://github.com/zobe123/HA-Weishaupt-WCM-COM/issues).

## License

This project is licensed under the MIT License. For more details, see the [LICENSE](LICENSE) file.

## Acknowledgments

This project is based on the work of [schmiegelt](https://github.com/schmiegelt/HA-Weishaupt-WCM-COM). Thank you for the inspiration and groundwork!
