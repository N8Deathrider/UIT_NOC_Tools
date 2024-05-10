#!/usr/bin/env python3

import pyperclip as pc

from nrc import ansi as a
from SwitchInfo import Switch
from SwitchInfo.Switch import gen_connection_dictionary
from auth import SSH

from netmiko import ConnectHandler

from rich.prompt import Prompt
from rich.prompt import IntPrompt
from rich.prompt import Confirm
from rich.rule import Rule
from rich import print as rprint

from sys import exit


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


def main_v2():

    sh_vvlan = ''
    conf_vvlan = ''
    conf_description = ''


    while True:
        description_query = input('Description? (y/n): ').lower()
        if description_query in ['y', 'n']:
            if description_query == 'y':
                description_text = input('Description: ')
                conf_description = f'description {description_text}\n'
            break
        else:
            print('Error please answer using either y for yes or n for no')


    while True:
        vvlan_query = input('Voice VLAN (y/n): ').lower()
        if vvlan_query in ['y', 'n']:
            if vvlan_query == 'y':
                vvlan_num = input('Voice VLAN number: ')
                sh_vvlan = f'sh vlan b | i {vvlan_num}\n'
                conf_vvlan = f'switchport voice vlan {vvlan_num}\n'
            break
        else:
            print('Error please answer using either y for yes or n for no')
    

    avlan_num = input('Access VLAN number: ')
    port_id = input('Port: ')


    config_template = (
        'terminal length 0\n'
        'sh clock\n'
        'sh users\n'
        f'sh vlan b | i {avlan_num}\n'
        f'{sh_vvlan}'
        f'sh int {port_id} status\n'
        f'sh mac address-table int {port_id}\n'
        f'sh run int {port_id}\n'
        'conf t \n'
        f'default int {port_id}\n'
        f'int {port_id}\n'
        f'{conf_description}'
        'switchport mode access\n'
        f'switchport access vlan {avlan_num}\n'
        f'{conf_vvlan}'
        'spanning-tree portfast\n'
        'shut\n'
        '\n\n'
        'no shut\n'
        'end\n'
        f'sh run int {port_id}\n'
        f'sh int {port_id} status\n'
        f'sh mac address-table int {port_id}\n'
        'sh clock\n'
        'sh users\n'
        )

    pc.copy(config_template)
    print(f'\n\n{config_template}\n\n{a.yellow_fg}This has automatically been copied to the clipboard{a.RESET}')


def main_v3():

    conf_description = ''
    sh_vvlan = ''
    conf_vvlan = ''


    if Confirm.ask("Description?"):
        description_text = Prompt.ask('Description')
        conf_description = f'description {description_text}\n'


    if Confirm.ask("Voice VLAN?"):
        vvlan_num = Prompt.ask('Voice VLAN Number')
        sh_vvlan = f'sh vlan b | i {vvlan_num}\n'
        conf_vvlan = f'switchport voice vlan {vvlan_num}\n'


    avlan_num = Prompt.ask('Access VLAN Number')
    port_id = Prompt.ask('Port')


    start_message = f'### Starting configuration of {port_id} ###'
    start_message_border = '#' * len(start_message)


    end_message = f'### Configuration of {port_id} complete ###'
    end_message_border = '#' * len(end_message)


    config_template = (
        'terminal length 0\n'
        f'{start_message_border}\n'
        f'{start_message}\n'
        f'{start_message_border}\n'
        'sh clock\n'
        'sh users\n'
        f'sh vlan b | i {avlan_num}\n'
        f'{sh_vvlan}'
        f'sh int {port_id} status\n'
        f'sh mac address-table int {port_id}\n'
        f'sh run int {port_id}\n'
        'conf t \n'
        f'default int {port_id}\n'
        f'int {port_id}\n'
        f'{conf_description}'
        'switchport mode access\n'
        f'switchport access vlan {avlan_num}\n'
        f'{conf_vvlan}'
        'spanning-tree portfast\n'
        'shut\n'
        '\n\n'
        'no shut\n'
        'end\n'
        f'sh run int {port_id}\n'
        f'sh int {port_id} status\n'
        f'sh mac address-table int {port_id}\n'
        'sh clock\n'
        'sh users\n'
        f'{end_message_border}\n'
        f'{end_message}\n'
        f'{end_message_border}\n'
    )

    pc.copy(config_template)
    print(f'\n\n{config_template}\n\n{a.yellow_fg}This has automatically been copied to the clipboard{a.RESET}')


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

    access_vlan_number = IntPrompt.ask('Access VLAN Number')  # Get the access vlan number
    interface_ids = Prompt.ask('Port(s)').split(",")  # Get the interface id

    # TODO: add description to the top of the commands listing all ports to be configured and to what vlan(s)
    pre_config_commands = ["show clock", "show users", f"show vlan brief | include ({access_vlan_number}|{desired_voice_vlan_number})_"] if voice_vlan else ["show clock", "show users", f"show vlan brief | include {access_vlan_number}"]

    print("Now attempting to configure the requested interface(s)")
    with ConnectHandler(**switch.connection_dictionary(SSH.username, SSH.password)) as connection:
        output += connection.find_prompt()
        for command in pre_config_commands:
            output += connection.send_command(
                command_string=command,
                strip_prompt=False,
                strip_command=False
            )

        if voice_vlan and description:
            for interface_id in interface_ids:
                output += connection.send_config_set(
                    config_commands=config_cmds_gen(
                        interface_id=interface_id,
                        access_vlan=access_vlan_number,
                        voice_vlan=desired_voice_vlan_number,
                        description=desired_description
                    ),
                    cmd_verify=True,
                    strip_prompt=False,
                    strip_command=False
                )
        elif voice_vlan:
            for interface_id in interface_ids:
                output += connection.send_config_set(
                    config_commands=config_cmds_gen(
                        interface_id=interface_id,
                        access_vlan=access_vlan_number,
                        voice_vlan=desired_voice_vlan_number
                    ),
                    cmd_verify=True,
                    strip_prompt=False,
                    strip_command=False
                )
        elif description:
            for interface_id in interface_ids:
                output += connection.send_config_set(
                    config_commands=config_cmds_gen(
                        interface_id=interface_id,
                        access_vlan=access_vlan_number,
                        description=desired_description
                    ),
                    cmd_verify=True,
                    strip_prompt=False,
                    strip_command=False
                )
        else:
            for interface_id in interface_ids:
                output += connection.send_config_set(
                    config_commands=config_cmds_gen(
                        interface_id=interface_id,
                        access_vlan=access_vlan_number
                    ),
                    cmd_verify=True,
                    strip_prompt=False,
                    strip_command=False
                )


        output += connection.save_config()

    print("Here is the output of the config")
    rprint(r)
    print(output)
    rprint(r)


if __name__ == '__main__':
    try:
        main_v5()
    except KeyboardInterrupt:
        rprint(f"\n[b]Ctrl[/b] + [b]c[/b] detected... Exiting script")
        exit(130)
