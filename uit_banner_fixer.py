#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#TODO: Add description
"""

# Standard libraries
import argparse
import logging
from getpass import getpass
from sys import exit

# Third-party libraries
from rich.logging import RichHandler
from rich.console import Console
from netmiko import ConnectHandler, SSHDetect, BaseConnection
from netmiko import NetmikoAuthenticationException

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


try:
    from auth import SSH
except ImportError as e:
    print("No auth.py file found.")
    class SSH:
        username = input("Enter your uNID: ")
        password = getpass("Enter your WIAN password: ")
        full = {"username": username, "password": password}


def get_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    :return: A namespace containing the parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="A script for fixing the banner on UIT switches."
    )
    parser.add_argument(
        "switch_address",
        type=str,
        help="The IP address of the switch.",
        nargs="+"  # Allow multiple switches to be passed
    )

    return parser.parse_args()


def switch_commands_generator(switch_name: str) -> list:
    """
    Generate a list of commands for configuring a switch.

    :param switch_name: The name of the switch.
    :param building_number: The number of the building where the switch is located.
    :param room_number: The number of the room where the switch is located.
    :return: A list of commands for configuring the switch.
    """
    return [
        "banner login ^",
        "\n",
        switch_name,
        "\n",
        "University of Utah Network:  All use of this device must comply",
        "with the University of Utah policies and procedures.  Any use of",
        "this device, whether deliberate or not will be held legally",
        "responsible.  See University of Utah Information Security",
        "Policy (4-004) for details.",
        "\n",
        "Problems within the University of Utah's network should be reported",
        "by calling the Campus Helpdesk at 581-4000, or via e-mail at",
        "helpdesk@utah.edu",
        "\n",
        "DO NOT LOGIN",
        "if you are not authorized by NetCom at the University of Utah.",
        "\n\n",
        "^",
    ]


def get_switch_hostname(connection: BaseConnection) -> str:
    """
    Get the hostname of a switch.

    :param connection: The connection to the switch.
    :return: The hostname of the switch.
    """
    return connection.send_command("show run", use_genie=True)["version"]["hostname"]


def main() -> None:
    """
    #TODO: Add description
    """
    ARGS = get_args()

    if ARGS.debug:
        log.setLevel(logging.DEBUG)

    log.debug(f"Arguments: {ARGS}")

    log.debug("Entering Switch Section")
    device_dict = {
        "device_type": "autodetect",
        "host": ARGS.switch_ip,
        "username": SSH.username,
        "password": SSH.password,
    }
    try:
        guesser = SSHDetect(**device_dict)
    except NetmikoAuthenticationException:
        log.error("Authentication error. Please check the username and password.")
        exit(EXIT_GENERAL_ERROR)
    best_match = guesser.autodetect()
    device_dict["device_type"] = best_match
    if ARGS.debug:
        dev_device_dict = device_dict.copy()
        dev_device_dict["password"] = "********"
        log.debug(f"Device dictionary: {device_dict}")


if __name__ == "__main__":
    try:
        # main()
        raise NotImplementedError("This script is not yet finished.")
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
