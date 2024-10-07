#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The purpose of this script is to make the trunk interfaces follow the standard 
set by the UIT team in [KB0017177](https://uofu.service-now.com/kb_view.do?preview_article=true&sys_kb_id=e61caa891b5c8d50247ceac0604bcbf4#EquipmentNamingConvention-Port/Interface)

The script will ensure that their descriptions are set to:
    'key:(local interface):(short neighbor switch name):(neighbor interface)'.

For example, if the trunk interface is Gi1/0/1 and the neighbor switch is SW2:
    Local Switch Name: SW1
    Local Switch Interface: Gi1/0/1
    Neighbor Switch Name: SW2
    Neighbor Switch Interface: Te1/0/1

    The description on Gi1/0/1 should be 'key:Gi1/0/1:SW2:Te1/0/1'.

The short name is the first two characters of the interface name followed by the interface number.
For example, 'GigabitEthernet7/30' would be 'Gi7/30' and 'TenGigabitEthernet1/1/1' would be 'Te1/1/1'.

The script can return the following exit codes:
    0 - No errors
    1 - General error
    130 - Ctrl+C

Use the -h or --help argument to get help on how to use the script.
"""
# Standard libraries
import argparse
from getpass import getpass
from pathlib import Path
from threading import Thread
from shutil import get_terminal_size
from sys import exit

# Third-party libraries
import arrow
from rich_argparse import RichHelpFormatter
from netmiko import ConnectHandler
from netmiko import SSHDetect
from netmiko.exceptions import AuthenticationException
from netmiko.exceptions import SSHException
from netmiko.exceptions import ConnectionException


try:  # Try to import the username and password from the auth.py file
    from auth import SSH  # Import the SSH class from the auth.py file
    USERNAME = SSH.username  # Get the username from the SSH class
    PASSWORD = SSH.password  # Get the password from the SSH class
except ImportError:  # If the auth.py file does not exist
    USERNAME = input("Enter the username: ")  # Prompt the user for the username
    PASSWORD = getpass("Enter the password: ")  # Prompt the user for the password securely (the password will not be shown exactly like in the terminal normally)


# Standard exit codes
EXIT_SUCCESS = 0  # No errors
EXIT_GENERAL_ERROR = 1  # General error
EXIT_INVALID_ARGUMENT = 120  # Invalid argument to exit
EXIT_KEYBOARD_INTERRUPT = 130  # Keyboard interrupt (Ctrl+C)


def get_args():
    """
    Get the arguments from the command line.

    Returns:
        argparse.Namespace: The arguments from the command line.
    """
    parser = argparse.ArgumentParser(formatter_class=RichHelpFormatter)  # Instantiate the parser

    # Add the IP address argument to the parser
    parser.add_argument('ip', nargs='*', help='Space-separated list of IP addresses')

    # Add the yes argument to the parser
    parser.add_argument('-y', '--yes', action='store_true', help='Answer yes to all questions')

    # Add the no argument to the parser
    parser.add_argument('-n', '--no', action='store_true', help='Answer no to all questions')

    # Add the dev argument to the parser
    parser.add_argument('--dev', action='store_true', help='Enable development mode')

    # Return the arguments from the command line
    return parser.parse_args()


ARGUMENTS = get_args()  # Get the arguments from the command line


def print_divider():
    """
    Prints a divider to separate the output for each IP address.

    Returns:
        None
    """
    print('-' * get_terminal_size()[0])  # Print a divider


def key_interfaces_folder() -> str:
    """
    Creates a folder named "key_interfaces" in the user's documents directory.

    Returns:
        str: The path of the created folder.
    """
    home_dir = Path.home()  # Get the user's home directory
    library_dir = home_dir / "Library"  # Get the user's library directory
    cloud_storage_dir = library_dir / "CloudStorage"  # Get the user's cloud storage directory
    box_dir = cloud_storage_dir / "Box-Box"  # Get the user's Box directory
    key_interfaces_dir = box_dir / "key_interfaces"  # Create the path for the "key_interfaces" folder

    if ARGUMENTS.dev:  # If development mode is enabled
        key_interfaces_dir = key_interfaces_dir / "dev"  # Add the "dev" folder to the path

    key_interfaces_dir.mkdir(parents=True, exist_ok=True)  # Create the "key_interfaces" folder if it doesn't exist

    return str(key_interfaces_dir)  # Return the path of the created folder as a string


def get_ip_addresses() -> list[str]:
    """
    Retrieves a list of IP addresses from either the command line arguments or user input.

    Returns:
        list[str]: A list of IP addresses without duplicate entries.
    """

    if ARGUMENTS.ip:  # If the IP address argument was given, use it
        ip_addresses = ARGUMENTS.ip  # Get the IP addresses from the command line arguments
    else:  # If the IP address argument was not given, prompt the user for a space-separated list of IP addresses
        while True:
            ip_addresses = input("Enter a space-separated list of IP addresses: ").split(" ")  # Prompt the user for a space-separated list of IP addresses
            if ip_addresses:  # If the user entered at least one IP address
                break  # Break out of the loop
            else:  # If the user did not enter at least one IP address
                print("Please enter at least one IP address.") # Print an error message

    ip_addresses = list(set(ip_addresses))  # Remove duplicate entries from the list

    return ip_addresses  # Return the list of IP addresses without duplicate entries


def gen_connection_dictionary(switch_ip: str, username: str, password: str, log_folder: str) -> dict[str, str]:
    """
    Generates a connection dictionary for establishing a connection to the switch.

    Args:
        switch_ip (str): The IP address of the switch.
        username (str): The username for authentication.
        password (str): The password for authentication.

    Returns:
        dict[str, str]: The connection dictionary containing the switch IP, username, password, and device type.
    """

    # Create the connection dictionary
    now = arrow.now().format("YYYY-MM-DD_HH:mm:ss")  # Get the current date and time
    connection_dictionary = {
        "username": username,
        "password": password,
        "host": switch_ip,
        "session_log": f"{log_folder}/{switch_ip}_{now}_switch_output.log",
        "device_type": "autodetect",
    }

    guesser = SSHDetect(**connection_dictionary)  # Instantiate the SSHDetect class

    connection_dictionary['device_type'] = guesser.autodetect()  # Set the device type in the connection dictionary

    return connection_dictionary  # Return the connection dictionary


def check_trunk_interfaces(ip_address):
    """
    Check the trunk interfaces of the given IP addresses to ensure that their descriptions follow the standard.

    The standard for trunk interface descriptions is as follows:
    - The description should start with the keyword 'key'.
    - The keyword is followed by the local interface, neighbor switch, and neighbor interface, separated by colons.
    - Example: 'key:Gi1/0/1:SW2:Gi2/0/1'

    Args:
        ip_address (str): IP address to check.

    Returns:
        None
    """
    log_folder = key_interfaces_folder()  # Get the path of the "key_interfaces" folder
    try:  # Try to connect to the switch
        with ConnectHandler(**gen_connection_dictionary(switch_ip=ip_address, username=USERNAME, password=PASSWORD, log_folder=log_folder)) as net_connect:  # Connect to the switch
            need_to_write = False  # Initialize the need_to_write variable
            output = net_connect.send_command("show interface trunk", use_genie=True)["interface"]  # Get the trunk interfaces
            for interface in output:  # Iterate through the trunk interfaces
                if interface.lower().startswith("po"):  # If the interface is a port-channel
                    continue  # Skip the rest of the loop and go to the next interface
                neighbor = net_connect.send_command(f"show cdp neighbor {interface}", use_textfsm=True)[0]  # Get the neighbor information

                #TODO: Check if this is the correct way to check if the neighbor information is empty
                if neighbor == "C":  # If the neighbor information is empty
                    print(f"[!] {ip_address} - {interface} did not have cdp neighbor information.", flush=True)  # Print that the neighbor information was not found
                    continue  # Skip the rest of the loop and go to the next interface

                if not neighbor["neighbor"].lower().startswith(("sx", "dx", "r")):  # If the neighbor is not a switch
                    print(f"[!] {ip_address} - {interface} neighbor is not a switch.")
                    continue  # Skip the rest of the loop and go to the next interface

                # Get the local interface and shorten it
                local_interface = f"{neighbor['local_interface'][:2]}{neighbor['local_interface'].split()[-1]}"

                # Get the neighbor interface and shorten it
                neighbor_interface = f"{neighbor['neighbor_interface'][:2]}{neighbor['neighbor_interface'].split()[-1]}"

                # Get the neighbor switch name and remove the domain name
                neighbor_switch = neighbor['neighbor'].split('.')[0]

                # Get the correct description
                correct_description = f"key:{local_interface}:{neighbor_switch}:{neighbor_interface}"

                # Print the expected description
                print(f"{ip_address} - {interface} should have description '{correct_description}'", flush=True)

                if ARGUMENTS.no:  # If the no argument was given
                    continue
                elif (ARGUMENTS.yes or input("Should the description be changed? (y/n) ").lower() == "y") and not ARGUMENTS.no:  # If the user answered yes or the yes argument was given
                    if not need_to_write:  # If the need_to_write variable is False
                        need_to_write = True  # Set the need_to_write variable to True
                    net_connect.send_config_set(  # Send the configuration commands to the switch
                        [
                            f"interface {interface}",  # Go to the interface
                            f"description {correct_description}"  # Set the description
                        ]
                    )
                    print(f"{ip_address} - {interface} should now have description '{correct_description}'")

            if need_to_write:  # If the need_to_write variable is True
                net_connect.save_config()  # Save the configuration
                need_to_write = False  # Reset the need_to_write
    except ConnectionError:  # If a connection error occurred, print the error
        print(f"[!!!] Connection error occurred for {ip_address}.")
    except TimeoutError:  # If a timeout error occurred, print the error
        print(f"[!!!] Timeout error occurred for {ip_address}.")
    except AuthenticationException:  # If an authentication error occurred, print the error
        print(f"[!!!] Authentication error occurred for {ip_address}.")
    except SSHException:  # If an SSH error occurred, print the error
        print(f"[!!!] SSH error occurred for {ip_address}.")
    except ConnectionException:  # If a connection error occurred, print the error
        print(f"[!!!] Connection error occurred for {ip_address}.")
    except Exception as e:  # If an unknown error occurred, print the error
        print(f"[!!!] An error occurred for {ip_address} - {e}.")


def main():
    """
    Main function of the script.

    Returns:
        None
    """
    chunk_size = 50 # Set the chunk size
    ip_addresses = get_ip_addresses()  # Get the IP addresses
    threads = []  # Initialize the threads list

    print_divider()
    print(f"Starting to check trunk interfaces for {len(ip_addresses)} switches.")
    print_divider()

    for i in range(0, len(ip_addresses), chunk_size):  # Iterate through the IP addresses
        chunk = ip_addresses[i:i + chunk_size]  # Get a chunk of IP addresses
        for ip_address in chunk:  # Iterate through the chunk of IP addresses
                thread = Thread(target=check_trunk_interfaces, args=(ip_address,))  # Create a thread for the IP address
                threads.append(thread)  # Add the thread to the threads list
                thread.start()  # Start the thread

        for thread in threads:  # Iterate through the threads
            thread.join()  # Wait for the thread to finish

    print_divider()
    print(f"Finished checking trunk interfaces for {len(ip_addresses)} switches.")
    print_divider()


if __name__ == "__main__":  # If the script is being run directly
    try:  # Try to run the script
        main()  # Run the script
        exit(EXIT_SUCCESS)  # Exit with status code 0 (no errors)
    except KeyboardInterrupt:  # If the user pressed Ctrl+C
        print("\nExiting... User pressed Ctrl+C.")
        exit(EXIT_KEYBOARD_INTERRUPT)  # Exit with status code 130 (Ctrl+C)
    except Exception as e:  # If an unknown error occurred
        print(f"An unexpected error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)  # Exit with status code 1 (general error)
