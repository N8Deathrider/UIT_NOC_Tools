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
from netmiko import BaseConnection
from rich.prompt import Prompt
from rich.rule import Rule
from rich.console import Console
from rich.logging import RichHandler
from rich.highlighter import RegexHighlighter
from rich.theme import Theme
import pyperclip as pc
from SwitchInfo import Switch

# Local libraries
from uit_style import style_switch_output
from uit_style import output_highlighting

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


def style_gen() -> tuple[type[RegexHighlighter], Theme]:
    """
    Generate the syntax highlighter and theme for the switch configuration output.
    """

    name_fixes = (
        ("-", "_"),
        ("/", ""),
        (" ", "_"),
    )

    class SyntaxHighlighter(RegexHighlighter):
        """
        Syntax highlighter for the switch configuration output.
        """

        base_style = "output."
        highlights = []
        for line in output_highlighting:
            name = line[2]
            for fix in name_fixes:
                name = name.replace(*fix)
            match = line[0]
            highlights.append(f"(?P<{name}>{match})")

    theme_map = {}
    for line in output_highlighting:
        name = line[2].replace("-", "_").replace("/", "").replace(" ", "_")
        for fix in name_fixes:
            name = name.replace(*fix)
        theme_map[f"output.{name}"] = line[1]

    return SyntaxHighlighter, Theme(theme_map)


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
        "-q",
        "--quiet",
        help="Suppress printing switch output",
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

    parser.add_argument(
        "--dry-run",
        "-dr",
        help="Do not make any changes to the switch",
        action="store_true",
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--copy",
        "-c",
        dest="copy",
        help="Copy the output to the clipboard without styling",
        action="store_true",
    )
    group.add_argument(
        "--no-copy",
        "-nc",
        dest="no_copy",
        help="Do not copy the switch output to the clipboard",
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


# TODO: find a better way to do this so that the dry run commands are not repeated
# making it easier to maintain when changes are made
def dry_run_cmds_gen(
    interface_id: str,
    access_vlan: str | int,
    voice_vlan: str | int | None = None,
    description: str | None = None,
) -> list[str]:
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
        f"#  DryRun Configuration {interface_id} Start  #",
        f"do show interface {interface_id} status",
        f"do show mac address-table interface {interface_id}",
        f"do show running-config interface {interface_id}",
        f"# Would now run: default interface {interface_id}",
        f"# Would now run: interface {interface_id}",
        "# Would now run: shutdown",
        "# Would now run: switchport mode access",
        f"# Would now run: switchport access vlan {access_vlan}",
        "# Would now run: spanning-tree portfast",
        "# Would now run: no shutdown",
        "# Would now run: exit",
        f"do show running-config interface {interface_id}",
        f"do show interface {interface_id} status",
        f"do show mac address-table interface {interface_id}",
        f"#  DryRun Configuration {interface_id} End  #",
    ]

    if voice_vlan:
        cmds.insert(8, f"# Would now run: switchport voice vlan {voice_vlan}")

    if description:
        cmds.insert(7, f"# Would now run: description {description}")

    return cmds


def config_cmds_gen(
    interface_id: str,
    access_vlan: str | int,
    voice_vlan: str | int | None = None,
    description: str | None = None,
) -> list[str]:
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
        f"show vlan brief | include {access_vlan}_",
    ]

    if voice_vlan:
        cmds[2] = f"show vlan brief | include ({access_vlan}|{voice_vlan})_"

    return cmds


def validate_vlans(connection: BaseConnection, vlan_id: int) -> bool:
    """
    Validate the provided VLAN ID.

    Args:
        connection (BaseConnection): The connection to the switch.
        vlan_id (int): The VLAN ID to validate.

    Returns:
        bool: True if the VLAN ID is valid, False otherwise.
    """
    vlans = connection.send_command("show vlan", use_textfsm=True)
    for vlan in vlans:
        if vlan["vlan_id"] == str(vlan_id):
            return True
    return False


def validate_interface(connection: BaseConnection, interface_id: str) -> bool:
    """
    Validate the provided interface ID.

    Args:
        connection (BaseConnection): The connection to the switch.
        interface_id (str): The interface ID to validate.

    Returns:
        bool: True if the interface ID is valid, False otherwise.
    """
    response = connection.send_command(f"show interface {interface_id} status")
    return "% Invalid input detected at '^' marker." not in response


def main():
    """
    Main function for configuring a switch.

    This function takes command line arguments, connects to a switch, and performs the configuration based on the provided arguments.

    Args:
        None

    Returns:
        None
    """
    args = get_args()
    SyntaxHighlighter, theme = style_gen()
    console = Console(highlighter=SyntaxHighlighter(), theme=theme)

    if args.debug:  # Set log level to debug if debug is set
        log.setLevel(logging.DEBUG)

    log.debug(f"Arguments: {args}")  # Log the arguments

    pre_config_commands = pre_config_commands_gen(args.access_vlan, args.voice_vlan)
    log.debug(f"Pre-configuration commands: {pre_config_commands}")

    with console.status("[green]Getting switch details...") as status:
        switch = Switch(args.switch)

        status.update("Connecting to switch...")
        with ConnectHandler(**switch.connection_dictionary(USERNAME, PASSWORD)) as connection:
            status.update("Validating Access VLAN...")
            if not validate_vlans(connection, args.access_vlan):
                status.stop()
                log.error(f"Access VLAN {args.access_vlan} is not valid.")
                exit(EXIT_INVALID_ARGUMENT)  # TODO: look into possibly instead configuring the VLAN if trunked
            if args.voice_vlan:
                status.update("Validating Voice VLAN...")
                if not validate_vlans(connection, args.voice_vlan):
                    status.stop()
                    log.error(f"Voice VLAN {args.voice_vlan} is not valid.")
                    exit(EXIT_INVALID_ARGUMENT)  # TODO: look into possibly instead configuring the VLAN if trunked
            for interface_id in args.interfaces:
                status.update(f"Validating interface {interface_id} exists...")
                if not validate_interface(connection, interface_id):
                    status.stop()
                    log.error(f"Interface {interface_id} is not valid.")
                    exit(EXIT_INVALID_ARGUMENT)
            status.update("Validations complete...")
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
                if args.dry_run:  # If dry run is set, generate dry run commands replacing the actual commands
                    config_commands = dry_run_cmds_gen(
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

            if not args.dry_run:
                status.update("Saving configuration...")
                output += connection.save_config()
        status.update("Configuration complete, disconnecting...")

    if not args.quiet:
        console.print(Rule(title="[bold red]Switch Configuration Output", style="red", align="left"), width=100)
        console.print(output, highlight=True)
        console.print(Rule(title="[bold red]End of Output", style="red", align="left"), width=100)

        if args.no_copy:
            return

        if not args.copy:
            output = f"[code]{style_switch_output(output)}[/code]"

        pc.copy(output)
        console.print("Output copied to clipboard." if args.copy else "Styled output copied to clipboard.")


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
