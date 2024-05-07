#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script retrieves the uptime of a switch or switches and displays the information.

The script uses command line arguments to specify the switch address(es) and an optional debug flag.
It imports the Switch class from the SwitchInfo module to interact with the switches.
The uptime information is retrieved from the switch and displayed using the rich library for formatting.

Usage:
    python uit_uptime.py [-d] switch [switch ...]

Arguments:
    switch: The switch address(es) to retrieve uptime information for.

Exit Codes:
    0: No errors.
    1: General error.
    120: Invalid argument to exit.
    130: Keyboard interrupt (Ctrl+C).
"""

# Standard libraries
import logging
from sys import exit
import argparse

# Third-party libraries
from rich.logging import RichHandler
from rich import print as rprint

# Local libraries
from SwitchInfo import Switch

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
logging.getLogger("paramiko").setLevel(logging.WARNING)


def get_args() -> argparse.Namespace:
    """
    Get command line arguments for getting the uptime of a switch or switches.

    Returns:
        argparse.Namespace: The parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description="Get the uptime of a switch or switches.")

    parser.add_argument("-d", "--debug", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("switch", type=str, help="The switch address.", nargs="+")

    return parser.parse_args()


def main() -> None:
    """
    This is the main function that performs the main logic of the program.

    It retrieves command line arguments, sets up the message template, and iterates over the specified switches to calculate and display their uptime.

    Args:
        None

    Returns:
        None
    """
    ARGS = get_args()
    MESSAGE = "[cyan]The switch [purple]\[[green]{switch}[purple]][cyan] has been up for [purple]\[[green]{standard_date}[purple]][cyan] days; it was restarted was [purple]\[[green]{nice_date}[purple]][cyan] reason is [purple]\[[green]{reason}[purple]][cyan]"

    if ARGS.debug:
        log.setLevel(logging.DEBUG)

    log.debug(f"Arguments: {ARGS}")

    for current_switch in ARGS.switch:
        switch: Switch = Switch(current_switch)
        uptime = switch.uptime
        log.debug(f"Uptime: {uptime}")
        rprint(MESSAGE.format(switch=current_switch, standard_date=uptime[0], nice_date=uptime[1].format("ddd, MMM D YYYY [a]t, h:mm A"), reason=uptime[2]))


if __name__ == "__main__":
    try:
        main()
        exit(EXIT_SUCCESS)
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
