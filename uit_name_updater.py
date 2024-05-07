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
import webbrowser

# Third-party libraries
from rich.logging import RichHandler
from u1377551 import login_duo
from netmiko import ConnectHandler, SSHDetect

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

session = login_duo()

def get_args() -> argparse.Namespace:
    """
    Parse command line arguments and return the parsed arguments as a Namespace object.

    This function uses the argparse module to define and parse command line arguments.
    It expects the following arguments:
    - function_descriptor: The descriptor for the switch type. 'dx' for distribution switches and 'sx' for access switches.
    - count: The count of the type of device in the same room.
    - building_number: The building number where the switch is located. (Will be padded with 0's to 4 digits)
    - building_short_name: The short name of the building where the switch is located.
    - room_number: The room number where the switch is located. (Will be padded with 0's to 4 digits)
    - distribution_node: The distribution node where the switch is connected.
    - switch_ip: The IP address of the switch.

    Returns:
        argparse.Namespace: The parsed command line arguments.
    """
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
        type=validate_ip_address,  # Validate the IP address
        help="The IP address of the switch.",
        metavar="SWITCH_IP"
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help=argparse.SUPPRESS  # Hide the debug option from the help message
    )

    return parser.parse_args()


def validate_ip_address(ip: str) -> str:
    """
    Validates the given IP address.

    Args:
        ip (str): The IP address to validate.

    Returns:
        str: The validated IP address.

    Raises:
        argparse.ArgumentTypeError: If the IP address is invalid.
    """
    try:
        ipaddress.ip_address(ip)
        return ip
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid IP address")


def name_generator(
        function_descriptor: str,
        count: str,
        building_number: str,
        building_short_name: str,
        room_number: str,
        distribution_node: str
    ) -> str:
    """
    Generates a name for a network device based on the given parameters.

    Args:
        function_descriptor (str): The function descriptor for the device.
        count (str): The count of the device.
        building_number (str): The building number of the device. (Padded with 0's to 4 digits)
        building_short_name (str): The short name of the building.
        room_number (str): The room number of the device. (Padded with 0's to 4 digits)
        distribution_node (str): The distribution node of the device.

    Returns:
        str: The generated name for the network device.
    """
    building_short_name = building_short_name.replace(" ", "")  # Remove spaces from the building short name

    if building_short_name[0].isnumeric():  # If the building short name starts with a number
        building_short_name = f"-{building_short_name}"  # Add a hyphen to the beginning of the building short name

    switch_name = f"{function_descriptor}{count}-{building_number.zfill(4)}{building_short_name}-{room_number.zfill(4)}-{distribution_node}".lower()

    log.debug(f"Generated Switch Name: {switch_name}")

    return switch_name


def location_generator(building_number: str, room_number: str) -> str:
    """
    Generates a location string for a network device based on the given building and room numbers.

    Args:
        building_number (str): The building number of the device. (Padded with 0's to 4 digits)
        room_number (str): The room number of the device. (Padded with 0's to 4 digits)

    Returns:
        str: The generated location string for the network device.
    """
    return f"Bldg. {building_number.zfill(4)} Room {room_number.zfill(4)}"


def switch_commands_generator(switch_name: str, building_number: str, room_number: str) -> list:
    """
    Generates a list of switch commands based on the provided switch name and location string.

    Args:
        switch_name (str): The name of the switch.
        location_string (str): The location string for the switch.

    Returns:
        list: A list of switch commands.

    """
    return [
        f"hostname {switch_name}",
        f"snmp-server location {location_generator(building_number, room_number)}",
        "banner login ^",
        "\n",
        f"{switch_name}.net.utah.edu",
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
        "^"
    ]


def orion_search(ip: str = None, dns: str = None, proptag: str = None, barcode: str = None) -> dict:
    """
    Performs a search in the Orion system based on the provided parameters.

    Args:
        ip (str, optional): The IP address to search for.
        dns (str, optional): The DNS name to search for.
        proptag (str, optional): The property tag to search for.
        barcode (str, optional): The barcode to search for.

    Returns:
        dict: The JSON response containing the search results.

    Raises:
        ValueError: If none of the search parameters (ip, dns, proptag, barcode) are provided.
    """
    
    if ip:
        r = session.get("https://toast.utah.edu/orion/switch", params={"ip": ip})
        r.raise_for_status()
        log.debug(f"Orion Search Response: {r.json()}")
        return r.json()

    if dns:
        r = session.get("https://toast.utah.edu/orion/switch", params={"dns": dns})
        r.raise_for_status()
        log.debug(f"Orion Search Response: {r.json()}")
        return r.json()

    if proptag:
        r = session.get(
            "https://toast.utah.edu/orion/switch", params={"proptag": proptag}
        )
        r.raise_for_status()
        log.debug(f"Orion Search Response: {r.json()}")
        return r.json()

    if barcode:
        r = session.get(
            "https://toast.utah.edu/orion/switch", params={"barcode": barcode}
        )
        r.raise_for_status()
        log.debug(f"Orion Search Response: {r.json()}")
        return r.json()

    raise (ValueError("You must provide an ip, dns, proptag, or barcode"))


def ddi_search(ip: str) -> dict:
    """
    Search for information about a host using its IP address.

    Args:
        ip (str): The IP address of the host to search for.

    Returns:
        dict: A dictionary containing information about the host.

    Raises:
        requests.HTTPError: If the HTTP request to the API fails.
    """
    r = session.get("https://toast.utah.edu/infoblox/host", params={"ip": ip})
    r.raise_for_status()
    log.debug(f"DDI Search Response: {r.json()}")
    return r.json()


def view_orion_node_page(node_id: int):
    """
    Opens the Orion Node Page for the given node ID.

    Parameters:
    - node_id (int): The ID of the node to view.

    Returns:
    None
    """
    node_url =  f"https://orion.sys.utah.edu/Orion/NetPerfMon/NodeDetails.aspx?NetObject=N:{node_id}"

    log.debug(f"Opening Orion Node Page: {node_url}")

    webbrowser.open(node_url)


def main() -> None:
    """
    #TODO: Add description
    """

    ARGS = get_args()

    if ARGS.debug:
        log.setLevel(logging.DEBUG)

    log.debug(f"Arguments: {ARGS}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
