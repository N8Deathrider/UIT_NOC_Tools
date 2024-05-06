#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#TODO: Add description
"""

# Standard libraries
import argparse
import ipaddress
import logging
from sys import exit

# Third-party libraries
from rich.logging import RichHandler

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
logging.getLogger("paramiko").setLevel(logging.WARNING)  # Suppress Paramiko info logs


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="This script figures out the proper name for a switch based on the "
        "current standards and updates it in the needed places."
    )

    parser.add_argument(
        "function_descriptor",
        type=str,
        help="The descriptor for the switch type. 'dx' for distribution switches and 'sx' for access switches.",
        metavar="FUNCTION_DESCRIPTOR",
        choices=["dx", "sx"]
    )

    parser.add_argument(
        "count",
        type=str,
        help="The count of the type of device in the same room.",
        metavar="COUNT"
    )

    parser.add_argument(
        "building_number",
        type=str,
        help="The building number where the switch is located. (Will be padded with 0's to 4 digits)",
        metavar="BUILDING_NUMBER"
    )

    parser.add_argument(
        "building_short_name",
        type=str,
        help="The short name of the building where the switch is located. (As specified in https://www.space.utah.edu/htdocs/requestBuildingList.php)",
        metavar="BUILDING_SHORT_NAME"
    )

    parser.add_argument(
        "room_number",
        type=str,
        help="The room number where the switch is located. (Will be padded with 0's to 4 digits)",
        metavar="ROOM_NUMBER"
    )

    parser.add_argument(
        "distribution_node",
        type=str,
        help="The distribution node where the switch is connected.",
        metavar="DISTRIBUTION_NODE"
    )

    parser.add_argument(
        "switch_ip",
        type=validate_ip_address,
        help="The IP address of the switch.",
        metavar="SWITCH_IP"
    )

    return parser.parse_args()


def validate_ip_address(ip: str) -> str:
    try:
        ipaddress.ip_address(ip)
        return ip
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid IP address")




def main() -> None:
    """
    #TODO: Add description
    """
    ...


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
