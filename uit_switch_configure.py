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
from rich.rule import Rule
from rich import print as rprint
from rich.logging import RichHandler
import pyperclip as pc

# Local libraries
from auth import SSH
from SwitchInfo import Switch
from SwitchInfo.Switch import gen_connection_dictionary


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
    #TODO: Add docstring
    """
    ...


def config_cmds_gen(
    interface_id: str,
    access_vlan: str | int,
    voice_vlan: str | int | None = None,
    description: str | None = None,
) -> list[str]:
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


def main_v5():
    """
    This improves on V4 by allowing a comma separated list of
    interfaces that will all be configured the same
    """
    r = Rule(style="red")
    output: str = ""

    switch = Switch(Prompt.ask("What switch?"))  # Get the switch

    description: bool = Confirm.ask("Description?")  # Get if there is a description
    if description:  # Set up description var if there is a description
        desired_description = Prompt.ask("\033[1F\033[0KDescription")

    voice_vlan: bool = Confirm.ask("Voice VLAN?")  # Get if there is a voice vlan
    if voice_vlan:  # Set up voice vlan vars if there is a voice vlan
        desired_voice_vlan_number = IntPrompt.ask("\033[1F\033[0KVoice VLAN Number")

    access_vlan_number = IntPrompt.ask(
        "Access VLAN Number"
    )  # Get the access vlan number
    interface_ids = Prompt.ask("Port(s)").split(",")  # Get the interface id

    # TODO: add description to the top of the commands listing all ports to be configured and to what vlan(s)
    pre_config_commands = (
        [
            "show clock",
            "show users",
            f"show vlan brief | include ({access_vlan_number}|{desired_voice_vlan_number})_",
        ]
        if voice_vlan
        else [
            "show clock",
            "show users",
            f"show vlan brief | include {access_vlan_number}",
        ]
    )

    print("Now attempting to configure the requested interface(s)")
    with ConnectHandler(
        **switch.connection_dictionary(SSH.username, SSH.password)
    ) as connection:
        output += connection.find_prompt()
        for command in pre_config_commands:
            output += connection.send_command(
                command_string=command, strip_prompt=False, strip_command=False
            )

        if voice_vlan and description:
            for interface_id in interface_ids:
                output += connection.send_config_set(
                    config_commands=config_cmds_gen(
                        interface_id=interface_id,
                        access_vlan=access_vlan_number,
                        voice_vlan=desired_voice_vlan_number,
                        description=desired_description,
                    ),
                    cmd_verify=True,
                    strip_prompt=False,
                    strip_command=False,
                )
        elif voice_vlan:
            for interface_id in interface_ids:
                output += connection.send_config_set(
                    config_commands=config_cmds_gen(
                        interface_id=interface_id,
                        access_vlan=access_vlan_number,
                        voice_vlan=desired_voice_vlan_number,
                    ),
                    cmd_verify=True,
                    strip_prompt=False,
                    strip_command=False,
                )
        elif description:
            for interface_id in interface_ids:
                output += connection.send_config_set(
                    config_commands=config_cmds_gen(
                        interface_id=interface_id,
                        access_vlan=access_vlan_number,
                        description=desired_description,
                    ),
                    cmd_verify=True,
                    strip_prompt=False,
                    strip_command=False,
                )
        else:
            for interface_id in interface_ids:
                output += connection.send_config_set(
                    config_commands=config_cmds_gen(
                        interface_id=interface_id, access_vlan=access_vlan_number
                    ),
                    cmd_verify=True,
                    strip_prompt=False,
                    strip_command=False,
                )

        output += connection.save_config()

    print("Here is the output of the config")
    rprint(r)
    print(output)
    rprint(r)


def main():
    """
    #TODO: Add docstring
    """
    ...


if __name__ == "__main__":
    try:
        main_v5()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
