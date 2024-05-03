#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A script to get interface info for each interface up to the router.
"""

# Standard library imports
import argparse
import logging
from sys import exit

# Third party imports
import netmiko
import pyperclip as pc
from netmiko import ConnectHandler
import netmiko.exceptions
from rich.logging import RichHandler
from rich.console import Console
from rich import print as rprint

# Local application/library specific imports
from SwitchInfo import Switch
from auth import SSH
from uit_style import style_switch_output, sn_code_tag_wrapper


# Standard exit codes
EXIT_SUCCESS = 0  # No errors
EXIT_GENERAL_ERROR = 1  # General error
EXIT_INVALID_ARGUMENT = 120  # Invalid argument to exit
EXIT_KEYBOARD_INTERRUPT = 130  # Keyboard interrupt (Ctrl+C)


# Set up logging
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logging.getLogger("paramiko").setLevel(logging.WARNING)
log: logging.Logger = logging.getLogger("rich")


def get_args() -> argparse.Namespace:
    """
    Parse command line arguments and return the parsed arguments as a Namespace object.
    """
    parser = argparse.ArgumentParser(
        description="Get interface info for each interface up to the router",
    )

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    parser.add_argument(
        "switch",
        type=str,
        help="Initial switch to connect to",
    )

    parser.add_argument(
        "interface",
        type=str,
        help="Starting interface to get info for",
    )

    return parser.parse_args()


def debug_mode():
    """
    Enable debug mode by setting the log level to DEBUG and logging a debug message.
    """
    log.setLevel("DEBUG")
    log.debug("Debug mode enabled")


def get_interface_info(connection: netmiko.BaseConnection, interface: str) -> str:
    """
    Get interface info for a given interface on a switch.
    """
    interface_info = connection.find_prompt()  # Add the prompt to the output so we know which switch it is
    interface_info += connection.send_command(f"show interface {interface}", strip_prompt=False, strip_command=False)
    return interface_info


def get_mac(connection: netmiko.BaseConnection) -> tuple[str, str]:
    """
    Retrieves the MAC address and VLAN information from the given connection.

    Args:
        connection (ConnectHandler): The connection object.

    Returns:
        Tuple[str, str]: A tuple containing the MAC address and VLAN information.

    """
    mac_info =  connection.send_command(
        f"show ip arp | exclude {connection.host}",
        use_textfsm=True
    )
    log.debug(f"Mac info: {mac_info}")

    mac = mac_info[0].get("mac")
    log.debug(f"Got mac address: {mac = }")

    vlan_id = mac_info[0].get("interface").removeprefix("Vlan")
    log.debug(f"Got vlan: {vlan_id = }")

    return mac, vlan_id


def get_upstream_interface(connection: netmiko.BaseConnection) -> str:
    """
    Retrieves the upstream interface for a given network connection.

    Args:
        connection (netmiko.BaseConnection): The network connection object.

    Returns:
        str: The upstream interface.

    """
    mac, vlan_id = get_mac(connection)
    upstream_interface_info = connection.send_command(
        f"show mac address-table address {mac} vlan {vlan_id} | include {vlan_id}",
    )
    log.debug(f"Upstream interface info: {upstream_interface_info = }")

    # I decided to do it like this because textfsm was
    # not working for this command consistently across devices
    upstream_interface = upstream_interface_info.split()[-1]
    log.debug(f"Upstream interface: {upstream_interface = }")

    return upstream_interface


def get_next_hop(connection: netmiko.BaseConnection, interface: str) -> dict:
    """
    Retrieves information about the next hop based on the given interface.

    Args:
        connection (netmiko.BaseConnection): The network connection object.
        interface (str): The interface to check for next hop.

    Returns:
        dict: A dictionary containing information about the next hop, including switch, fqdn, downstream_interface,
              downstream_interface_info, upstream_interface, and upstream_interface_info.

    Raises:
        Exception: If the next hop is not found.
    """
    neighbor_name = connection.send_command(
        f"show cdp neighbors {interface}",
        use_textfsm=True
    )[0].get("neighbor")
    log.debug(f"Neighbor name: {neighbor_name = }")

    neighbors = connection.send_command(
        f"show cdp neighbors detail",
        use_textfsm=True
    )
    log.debug(f"Neighbors: neighbors = {[neighbor.get('destination_host') for neighbor in neighbors]}")

    for neighbor in neighbors:
        log.debug(f"Checking neighbor: {neighbor.get('destination_host') = }")
        if neighbor.get("destination_host") == neighbor_name:
            return {
                "switch": neighbor.get("management_ip"),
                "fqdn": neighbor.get("destination_host"),
                "downstream_interface": neighbor.get("remote_port"),
                "downstream_interface_info": None,
                "upstream_interface": None,
                "upstream_interface_info": None,
            }
    else:
        raise Exception("Next hop not found")


def display_info(targets: dict):
    """
    Display information about the targets.

    Args:
        targets (dict): A dictionary containing information about the targets.

    Returns:
        str: A string containing the formatted information about the targets.
    """
    final_output = ""
    for target in targets:
        final_output += f"{target.get('fqdn') or target.get('switch')}:\n"
        final_output += style_switch_output(target["downstream_interface_info"])
        final_output += "<br>"
        final_output += style_switch_output(target["upstream_interface_info"])
        final_output += "<br><br>"
    return sn_code_tag_wrapper(final_output.removesuffix("<br><br>"))


def main():
    """
    Main function to run the script.
    """
    ARGS = get_args()
    console = Console()

    if ARGS.debug:  # Set log level to debug if debug flag is set
        debug_mode()
    log.debug(f"Arguments: {ARGS}")

    targets = [
        {
            "switch": ARGS.switch,
            "downstream_interface": ARGS.interface,
            "downstream_interface_info": None,  # This will be filled in later
            "upstream_interface": None,  # This will be filled in later
            "upstream_interface_info": None,  # This will be filled in later
        }
    ]

    # console.status is a context manager that displays a status message while the block of code is running
    # It is used here to display a status message while the data is being gathered and make the script look more professional
    with console.status("[bold green]Gathering data...") as status:

        for target in targets:
            log.debug(f"New target: {target = }")
            status.update(f"[bold green]Gathering data for {target.get('fqdn') or target.get('switch')}...")
            if target.get("fqdn","").startswith("r"):
                log.debug("Switch is a router. Breaking for loop and removing router from targets list.")
                targets.remove(target)
                break
            switch = Switch(target["switch"])
            with ConnectHandler(**switch.connection_dictionary(**SSH.full)) as connection:
                log.debug(f"Getting downstream interface info: {connection.host = } - {target['downstream_interface'] = }")
                target["downstream_interface_info"] = get_interface_info(connection, target["downstream_interface"])

                target["upstream_interface"] = get_upstream_interface(connection)
                log.debug(f"{target['upstream_interface'] = }")

                target["upstream_interface_info"] = get_interface_info(connection, target["upstream_interface"])

                next_target = get_next_hop(connection, target["upstream_interface"])
                log.debug(f"{next_target = }")

                targets.append(next_target)
                # log.debug(f"{targets = }")

    pc.copy(display_info(targets))
    rprint("[yellow]Output copied to clipboard")

    exit(EXIT_SUCCESS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT or 130)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR or 1)
