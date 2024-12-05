#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#TODO: Add description
"""

# Standard libraries
import logging
import argparse
import re
from ipaddress import ip_network
from sys import exit

# Third-party libraries
from pyperclip import copy
from pyperclip import paste
from rich import print as rprint
from rich.logging import RichHandler
from rich_argparse import RichHelpFormatter

# Local libraries


# Standard exit codes
EXIT_SUCCESS = 0  # No errors
EXIT_GENERAL_ERROR = 1  # General error
EXIT_INVALID_ARGUMENT = 120  # Invalid argument to exit
EXIT_KEYBOARD_INTERRUPT = 130  # Keyboard interrupt (Ctrl+C)


# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)
log: logging.Logger = logging.getLogger("rich")


re_vlan = re.compile(r"interface Vlan(\d+)")
re_ip = re.compile(r"ip address (\d+\.\d+\.\d+\.\d+) (\d+\.\d+\.\d+\.\d+)")
re_description = re.compile(r"description (.+)")


def get_args() -> argparse.Namespace:
    """
    Parses command-line arguments.
    Returns:
        argparse.Namespace: The parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Takes a vlan config from the clipboard and returns it in a more readable format.",
        formatter_class=RichHelpFormatter
    )

    return parser.parse_args()


def main() -> None:
    """
    #TODO: Add description
    """
    ARGS = get_args()  # Parse command-line arguments
    # Currently, the script does not take any arguments

    vlan_config = paste()

    network_address = re_ip.search(vlan_config).group(1)
    subnet_mask = re_ip.search(vlan_config).group(2)

    network = ip_network(f"{network_address}/{subnet_mask}", strict=False)

    formatted_config = f"""\
Vlan Number: {re_vlan.search(vlan_config).group(1)}
IP Address: {network_address}
Subnet Mask: {subnet_mask}
Network in CIDR notation: {network.with_prefixlen}
"""

    copy(formatted_config)
    print(formatted_config)
    rprint("[yellow]Coppied to clipboard")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
