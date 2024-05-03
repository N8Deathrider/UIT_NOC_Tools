# UIT NOC Tools

Welcome to UIT NOC Tools, a collection of utilities and resources for me while I'm working at the University Information Technology NOC desk.

## Overview

UIT NOC Tools is designed to assist in managing tickets and preforming other tasks for my job. It provides a set of tools and resources that can be used to streamline processes and improve overall efficiency.

## Features

- **uit_bsb**: A simple tracker to tell me the eta for the UofU BSB bus
- **uit_device_search**: This script performs a search for a specified item using an API and retrieves the results.
- **uit_key_interfaces**: This script checks the trunk interfaces of switches to ensure that their descriptions follow a specific standard.
- **uit_people**: This script allows users to search for and retrieve information about people from the University of Utah's online directory.
- **uit_route**: This script provides functions for routing requests to the appropriate queue and generating a formatted message with routing information and a Teams link.
- **uit_statusio**: This script retrieves status information from the status.io API and displays it in the terminal using the Rich library for enhanced formatting.
- **uit_style**: #TODO
- **uit_switch_configure**: This script allows users to configure network switch interfaces by running automated commands based off user input.
- **uit_uplink_check**: This script retrieves interface information for each interface up to the router.
- **uit_uptime**:This script retrieves the uptime of a switch or switches and displays the information.

## Installation

To use UIT NOC Tools, follow these steps:

1. Clone the repository: `git clone https://github.com/N8Deathrider/UIT_NOC_Tools.git`
2. Navigate to the cloned repository: `cd UIT_NOC_Tools`
<!-- 3. It's recommended to create a virtual environment to isolate your project: `python3 -m venv env`
4. Activate the virtual environment: 
   - On Mac/Linux: `source env/bin/activate`
   - On Windows: `.\env\Scripts\activate`
5. Install the required packages: `pip install -r requirements.txt` -->
3. Install the required packages: `pip install -r requirements.txt`

> [!NOTE]
> I usually will symlink each of these file to a different dir that's added to $PATH with a nicer looking name just for looks.
> For example: `ln -s ./uit_bsb.py ~/.local/bin/uit.bsb`

## Usage

Each tool can be run from the command line and all should have a `-h` or `--help`

## Contributing

Contributions are welcome! If you have any ideas, suggestions, or bug reports, please open an issue or submit a pull request.

## License

MIT License. See [LICENSE](LICENSE) for more information.

## Contact

For any inquiries or support, please contact me at nath001c@gmail.com.
