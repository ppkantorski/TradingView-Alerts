# TradingView Alerts

TradingViewAlerts is a Python script that allows you to automate the process of reading and processing alerts from TradingView and taking actions based on those alerts.

## Table of Contents
- [About](#about)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)

## About

TradingViewAlerts is a tool designed to simplify the process of interacting with TradingView alerts within your Python projects. Whether you're using TradingView for trading signals, technical analysis, or other purposes, this script can help you automate the handling of alerts.

## Features

- **Alert Parsing**: Automatically parse alerts received from TradingView.
- **Action Execution**: Define custom actions to take based on specific alerts.
- **Integration**: Easily integrate TradingView alerts into your trading or analysis workflow.
- **Customization**: Configure the script to fit your specific requirements.

## Installation

To use TradingViewAlerts, follow these installation steps:

1. Clone this repository to your local machine.
   ```git clone https://github.com/ppkantorski/TradingViewAlerts.git```

2. Navigate to the project directory.

   ```cd TradingViewAlerts```

3. Install the required Python dependencies.


## Usage

1. Configure the script by editing the config.json file. Add your TradingView credentials and define the actions to be taken for specific alerts.

2. Run the script.

    ```python tradingview_alerts.py```

3. The script will continuously monitor your TradingView alerts and execute actions based on the configured rules.

## Configuration

### `config.json`

The `config.json` file is used to configure the behavior of TradingViewAlerts. You can define the following parameters:

- `STRATEGY_COLUMNS`: List of columns to include in the strategy data.
- `CREDENTIALS_FILE`: The file containing your GMAIL API credentials.
- `TOKEN_FILE`: The file used to store authentication tokens.

Example `config.json`:

```json
{
    "STRATEGY_COLUMNS": [
        "Source",
        "Presets",
        "Message",
        "Timestamp",
        "Timeframe",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume"
    ],
    "CREDENTIALS_FILE": "client_secret.apps.googleusercontent.com.json",
    "TOKEN_FILE": "token.json"
}
```

### `telegram_config.json`
In addition to `config.json`, you can also configure Telegram integration using the `telegram_config.json` file. This file allows you to set up and manage your Telegram bot's API credentials.

Example `telegram_config.json`:
```json
{
    "chat_id": "-100000000",
    "token": "123456789:abcdefghijklmnop"
}
```

In this example, you should provide your specific Telegram bot's `chat_id` and `token`. These values are essential for configuring the Telegram integration correctly.

Please make sure to customize the `telegram_config.json` file with your Telegram bot's specific `chat_id` and `token` according to your requirements.


## Contributing

Contributions are welcome! If you have any ideas, improvements, or bug fixes, please open an issue or submit a pull request. Make sure to follow the project's coding style and guidelines.

## License

This project is licensed under the [CC-BY-NC-4.0 License](LICENSE).
