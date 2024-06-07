#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script is designed to configure a switch port on a Cisco switch
to a specified VLAN. It will also configure the port for voice VLAN
if requested. It will also configure the port with a description if
requested.
"""

# Standard libraries
import logging
import argparse
from sys import exit

# Third-party libraries
from netmiko import ConnectHandler
from rich.prompt import Prompt
from rich.prompt import IntPrompt
from rich.prompt import Confirm
from rich.panel import Panel
from rich.console import Console
from rich import print as rprint
from rich.logging import RichHandler
import pyperclip as pc

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
logging.getLogger("paramiko").setLevel(logging.WARNING)  # Set paramiko to only log warnings


def get_args() -> argparse.Namespace:
    """
    Parse command line arguments for configuring switch interfaces.

    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description="Configure switch interface(s)")
    parser.add_argument(
        "--debug",
        help=argparse.SUPPRESS,
        action="store_true",
    )

    parser.add_argument(
        "--voice-vlan",
        "-vv",
        dest="voice_vlan",
        help="Voice VLAN number",
        type=int,
    )
    parser.add_argument(
        "--description",
        "-d",
        dest="description",
        help="Description for the interface",
        type=str,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--copy",
        "-c",
        dest="copy",
        help="Copy the output to the clipboard",
        action="store_true",
    )
    group.add_argument(
        "--style",
        "-s",
        dest="style",
        help="Style the switch output and then copy it to the clipboard",
        action="store_true",
    )

    parser.add_argument(
        "switch",
        help="The switch to connect to",
        type=str,
    )
    parser.add_argument(
        "access_vlan",
        help="The access VLAN number",
        type=int,
    )
    parser.add_argument(
        "interfaces",
        help="The interface(s) to configure",
        type=str,
        metavar="interface",
        nargs="+",
    )

    return parser.parse_args()


def credentials() -> tuple[str, str]:
    """
    Get the username and password for the switch.

    Returns:
        tuple[str, str]: The username and password.
    """
    try:
        from auth import SSH
        username = SSH.username
        password = SSH.password
    except ImportError:
        log.warning("No stored authentication credentials found.")
        username = Prompt.ask("Username")
        password = Prompt.ask("SSH Password", password=True)
    return username, password


def config_cmds_gen(interface_id: str, 
                    access_vlan: str | int, 
                    voice_vlan: str | int | None = None, 
                    description: str | None = None) -> list[str]:
    """
    Generate a list of configuration commands for a given interface.

    Args:
        interface_id (str): The ID of the interface.
        access_vlan (str | int): The VLAN ID for access.
        voice_vlan (str | int | None, optional): The VLAN ID for voice traffic. Defaults to None.
        description (str | None, optional): The description for the interface. Defaults to None.

    Returns:
        list[str]: A list of configuration commands.

    """
    cmds = [
        f"#  Configuration {interface_id} Start  #",
        f"do show interface {interface_id} status",
        f"do show mac address-table interface {interface_id}",
        f"do show running-config interface {interface_id}",
        f"default interface {interface_id}",
        f"interface {interface_id}",
        "shutdown",
        "switchport mode access",
        f"switchport access vlan {access_vlan}",
        "spanning-tree portfast",
        "no shutdown",
        "exit",
        f"do show running-config interface {interface_id}",
        f"do show interface {interface_id} status",
        f"do show mac address-table interface {interface_id}",
        f"#  Configuration {interface_id} End  #",
    ]

    if voice_vlan:
        cmds.insert(8, f"switchport voice vlan {voice_vlan}")

    if description:
        cmds.insert(7, f"description {description}")

    return cmds


def pre_config_commands_gen(access_vlan: str | int, voice_vlan: str | int | None = None) -> list[str]:
    """
    Generate a list of pre-configuration commands.

    Args:
        access_vlan (str | int): The access VLAN number.
        voice_vlan (str | int | None, optional): The voice VLAN number. Defaults to None.

    Returns:
        list[str]: A list of pre-configuration commands.
    """
    cmds = [
        "show clock",
        "show users",
        f"show vlan brief | include {access_vlan}",
    ]

    if voice_vlan:
        cmds[2] = f"show vlan brief | include ({access_vlan}|{voice_vlan})_"

    return cmds


def main():
    """
    #TODO: Add docstring
    """
    args = get_args()
    console = Console()

    if args.debug:  # Set log level to debug if debug is set
        log.setLevel(logging.DEBUG)

    log.debug(f"Arguments: {args}")  # Log the arguments

    pre_config_commands = pre_config_commands_gen(args.access_vlan, args.voice_vlan)
    log.debug(f"Pre-configuration commands: {pre_config_commands}")

    with console.status("[green]Getting switch details...") as status:
        switch = Switch(args.switch)

        status.update("Connecting to switch...")
        with ConnectHandler(**switch.connection_dictionary(USERNAME, PASSWORD)) as connection:
            # TODO: Need to add validation for the access vlan, voice vlan, and interface ids to ensure they are valid and raise an error if they are not
            # Probably should go right here before we start configuring the switch with something like:
            # status.update("Validating arguments..")
            output = connection.find_prompt()
            for command in pre_config_commands:
                output += connection.send_command(
                    command_string=command, strip_prompt=False, strip_command=False
                )

            for interface_id in args.interfaces:
                status.update(f"Configuring interface {interface_id}...")
                config_commands = config_cmds_gen(
                    interface_id=interface_id,
                    access_vlan=args.access_vlan,
                    voice_vlan=args.voice_vlan,
                    description=args.description,
                )
                output += connection.send_config_set(
                    config_commands=config_commands,
                    cmd_verify=True,
                    strip_prompt=False,
                    strip_command=False,
                )

            status.update("Saving configuration...")
            output += connection.save_config()
        status.update("Configuration complete, disconnecting...")

    console.print(Panel(output, title="Configuration Output", border_style="red"), )

    if args.copy or args.style:
        if args.style:
            ...  # TODO: Add styling to the output from the uit_style module

        pc.copy(output)
        console.print("Styled output copied to clipboard." if args.style else "Output copied to clipboard.")


if __name__ == "__main__":
    try:
        USERNAME, PASSWORD = credentials()
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
