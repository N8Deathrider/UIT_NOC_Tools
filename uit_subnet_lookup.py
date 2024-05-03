#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script is used to look up a vlan on the routers are return the subnet mask, gateway, and vlan name in a nice format.
"""

# Standard libraries
import argparse
import logging
from sys import exit

# Third-party libraries
from rich.logging import RichHandler
from SwitchInfo import Switch

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


def get_args() -> argparse.Namespace:
    """
    Parse command line arguments and return the parsed arguments.

    Returns:
        argparse.Namespace: The parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="This script is used to look up a vlan on the routers are return the subnet mask, gateway, and vlan name in a nice format."
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help=argparse.SUPPRESS
    )

    parser.add_argument(
        "vlan",
        type=int,
        help="The vlan id to look up."
    )

    return parser.parse_args()


def main() -> None:
    """
    #TODO: Add description
    """

    ARGS = get_args()

    if ARGS.debug:
        log.setLevel(logging.DEBUG)
        log.debug("Debug level logging enabled.")

    # Command is `show run interface vlan <vlan_id>`


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
