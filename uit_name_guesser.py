#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#TODO: Add description
"""

# Standard libraries
import argparse
import logging
from socket import getfqdn
from sys import exit

# Third-party libraries
from rich.logging import RichHandler
from SwitchInfo import Switch

# Local libraries
from uit_building_lookup import get_table_data

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
    """"""
    parser = argparse.ArgumentParser(
        description="A script for guessing the name of a switch based on its IP address."
    )
    parser.add_argument("ip", type=str, help="The IP address of the switch.")
    return parser.parse_args()


def main() -> None:
    """
    #TODO: Add description
    """
    switch = Switch(get_args().ip)
    if switch.name.rack_number:
        print(f"{switch.name.function_descriptor} {switch.name.number} {switch.name.building_number} {switch.name.building_code} {switch.name.room_number}-{switch.name.rack_number} {switch.name.node} {switch.ip}")
    else:
        print(f"{switch.name.function_descriptor} {switch.name.number} {switch.name.building_number} {switch.name.building_code} {switch.name.room_number} {switch.name.node} {switch.ip}")


def main2() -> None:
    """"""
    prefer_correct_building_code = False
    table_data = get_table_data()
    fqdn = getfqdn(get_args().ip).removesuffix(".net.utah.edu").split("-")

    function_descriptor_and_number = list(fqdn.pop(0))
    number = function_descriptor_and_number.pop()
    function_descriptor = "".join(function_descriptor_and_number)

    building_number_and_code = fqdn.pop(0)

    if building_number_and_code.isdigit():
        building_number = building_number_and_code
        building_code = fqdn.pop(0)
    elif building_number_and_code[:4].isdigit():
        building_number = building_number_and_code[:4]
        building_code = building_number_and_code[4:]
    elif building_number_and_code[:3].isdigit():
        building_number = building_number_and_code[:3]
        building_code = building_number_and_code[3:]
    else:
        log.warning("Building number does not seem to be 3 or 4 digits long. Using backup method.")
        building_number = ""
        building_code = ""
        for char in building_number_and_code:
            if char.isdigit():
                building_number += char
            else:
                building_code += char
    building_number = building_number.lstrip("0")

    # Testing the get_table_data function
    building_data = table_data.loc[int(building_number)]
    building_data_code = building_data["Abbreviation"].lower()
    if building_code != building_data_code:
        if prefer_correct_building_code:
            # log.warning(f"Building code does not match. Expected: '{building_data_code}'. Got: '{building_code}'. Using expected value.")  # Disabled because it messes up the output when using as input for name changer
            building_code: str = building_data_code.replace(" ", "")
        else:
            # log.warning(f"Building code does not match. Expected: '{building_data_code}'. Got: '{building_code}'. Using provided value.")  # Disabled because it messes up the output when using as input for name changer
            pass
        building_code = building_code.removeprefix("_")

    node = fqdn.pop()

    room_number = "-".join(fqdn)

    # print(f"{fqdn=}\n{function_descriptor=}\n{number=}\n{building_number=}\n{building_code=}\n{room_number=}\n{node=}")  # DEBUG
    print(f"{function_descriptor} {number} {building_number} {building_code} {room_number} {node} {get_args().ip}")


if __name__ == "__main__":
    try:
        main2()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
