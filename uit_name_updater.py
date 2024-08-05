#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script is used to update the name of a network device in the UIT NOC Tools system.
It generates a new name for the device based on the given parameters and updates the name in the necessary places.
"""

# Standard libraries
import argparse
import ipaddress
import logging
from sys import exit
import webbrowser
from getpass import getpass
from socket import gethostbyname
from socket import gaierror
import urllib3
from threading import Thread

# Third-party libraries
from rich.logging import RichHandler
from rich.prompt import Confirm
from rich.table import Table
from rich import print as rprint
from uit_duo import Duo
from netmiko import ConnectHandler, SSHDetect, BaseConnection
from netmiko import NetmikoAuthenticationException
import orionsdk

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


try:
    from auth import UofU, SSH

    ORION_USERNAME, ORION_PASSWORD = f"ad\\{UofU.unid}", UofU.cisPassword
except ImportError:
    print("No auth.py file found.")
    uNID = input("Enter your uNID: ")
    ORION_PASSWORD = getpass("Enter your CIS password: ")
    WIAN_PASSWORD = getpass("Enter your WIAN password: ")
    ORION_USERNAME = f"ad\\{uNID}"
    class SSH:
        username = uNID
        password = WIAN_PASSWORD
        full = {
            "username": username,
            "password": password
        }


class Orion:
    def __init__(self, server, username: str, password: str):
        orionsdk.swisclient.requests.packages.urllib3.disable_warnings()
        self.swis = orionsdk.SwisClient(server, username, password, port=17778)

    def get_dev_info(self):
        """
        Fetches development status.

        Returns:
            str: Returns "Production" if url is sys.utah.edu, returns
            "Development" otherwise.
        """
        return "Production" if "sys.utah.edu" in self.swis.url else "Development"

    def get_switch(self, ip=None, proptag=None, barcode=None, dns_name=None) -> dict:
        """
        Get switch information by either IP, property tag, or barcode. This will
        return switch information. Note that all arguments are optional;
        however, at least one must be used to filter results.

        Args:
            ip (str): Optional - IP address of the switch.
            proptag (str): Optional - Property tag of the switch.
            barcode (str): Optional - Barcode of the switch.
            dns_name (str): Optional - DNS/hostname.

        Returns:
            Orion.SwitchData: An object with the most relevant switch returned.

        Raises:
            ValueError: Caused when no information is given.
        """
        result = ""
        query = "SELECT (URI, NodeID, IP, DNS, NodeName, Location) FROM Orion.Nodes "
        if ip:
            ip = ip.split("/")[0]  # get rid of CIDR just in case
            result = self.swis.query(query + f"WHERE IP='{ip}'")
        elif proptag or barcode:
            result = self.swis.query(
                query
                + "WHERE Location LIKE '%"
                + str(proptag if proptag else barcode)
                + "%'"
            )
        elif dns_name:
            result = self.swis.query(query + "WHERE DNS LIKE '%" + dns_name + "%'")
        else:
            raise ValueError("no information given")

        return result
    
    def change_orion_node_name(self, uri: str, new_name: str):
        """
        Changes the name of an Orion node.

        Parameters:
        - uri (str): The URI of the node to change.
        - new_name (str): The new name of the node.

        Returns:
        None
        """
        if not new_name.endswith(".net.utah.edu"):
            new_name = new_name + ".net.utah.edu"
        log.debug(f"Changing Orion Node Name: {new_name}")

        self.swis.update(uri, NodeName=new_name)


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


def name_generator(function_descriptor: str, count: str, building_number: str,
                   building_short_name: str, room_number: str, distribution_node: str) -> str:
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

    # This is a temp fix for when current room numbers are listed as 'mdf' rather than a proper number.
    # This will be removed once all room numbers are properly listed.
    # If proper room number is known, it should be used instead of 'mdf'.
    if room_number not in ["mdf", "lab"]:  # If the room number is not 'mdf' or 'lab' (temporary fix until all room numbers are properly listed)
        room_number = room_number.zfill(4) # Pad the room number with 0's to 4 digits

    switch_name = f"{function_descriptor}{count}-{building_number.zfill(4)}{building_short_name}-{room_number}-{distribution_node}".lower()

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
    Generate a list of commands for configuring a switch.

    :param switch_name: The name of the switch.
    :param building_number: The number of the building where the switch is located.
    :param room_number: The number of the room where the switch is located.
    :return: A list of commands for configuring the switch.
    """
    return [
        f"hostname {switch_name}",
        f"snmp-server location {location_generator(building_number, room_number)}",
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
        "^"
    ]


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
    duo = Duo(uNID=UofU.unid, password=UofU.cisPassword)
    session = duo.login()  #TODO: find a better place for this
    urllib3.disable_warnings()
    session.verify = False
    session.get("https://toast.utah.edu/login_helper")
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


def change_display_table(table_title: str, current_name: str, potential_name: str):
    """
    Creates a display table with the given table title, current name, and potential name.

    Args:
        table_title (str): The title of the table.
        current_name (str): The current name.
        potential_name (str): The potential name.

    Returns:
        Table: The display table with the title, current name, and potential name.
    """
    table = Table(title=table_title, show_header=False, style="red")

    table.add_row("[bold]Current Name:", current_name)
    table.add_row("[bold]Potential Name:", potential_name)

    return table


def padder(number):
    number_str = str(number)
    max_len = 4
    return [number_str.zfill(i) for i in range(len(number_str), max_len + 1)]


def change_switch_info(connection: BaseConnection, correct_name: str, building_number: str, room_number: str) -> None:
    """
    Updates the switch information with the correct name, building number, and room number.

    Args:
        connection (BaseConnection): The connection object used to communicate with the switch.
        correct_name (str): The correct name for the switch.
        building_number (str): The building number where the switch is located.
        room_number (str): The room number where the switch is located.

    Returns:
        None
    """
    switch_output = ""
    commands = switch_commands_generator(correct_name, building_number, room_number)
    switch_output += connection.send_config_set(commands)
    connection.set_base_prompt()
    switch_output += connection.save_config()
    log.debug(f"Output: {switch_output}")
    connection.disconnect()  # Disconnect from the switch
    log.debug("Switch connection closed.")


def main() -> None:
    """
    Main function for updating switch names in Orion and InfoBlox.

    This function performs the following steps:
    1. Connects to the Orion server.
    2. Retrieves command line arguments.
    3. Sets the log level based on the debug flag.
    4. Generates the correct switch name based on the provided arguments.
    5. Sets the domain name.
    6. Enters the switch section and detects the device type.
    7. Connects to the switch using SSH.
    8. Retrieves the current hostname of the switch.
    9. Checks if the current hostname matches the correct name.
    10. Asks for confirmation to change the switch name if necessary.
    11. Generates the switch commands to change the name.
    12. Sends the switch commands and saves the configuration.
    13. Enters the Orion section and retrieves the switch data from Orion.
    14. Checks if the current node name in Orion matches the correct name.
    15. Asks for confirmation to change the node name in Orion if necessary.
    16. Changes the node name in Orion.
    17. Exits the Orion section.
    18. Enters the InfoBlox section and retrieves the InfoBlox data for the switch.
    19. Checks if there is a mismatch between the switch name and the InfoBlox name.
    20. Prints a message if there is a mismatch.
    """

    orion = Orion("smg-hamp-p01.ad.utah.edu", ORION_USERNAME, ORION_PASSWORD)

    ARGS = get_args()

    if ARGS.debug:
        log.setLevel(logging.DEBUG)

    log.debug(f"Arguments: {ARGS}")

    correct_name = name_generator(ARGS.function_descriptor, ARGS.count, ARGS.building_number, ARGS.building_short_name, ARGS.room_number, ARGS.distribution_node)
    domain_name = ".net.utah.edu"
    full_name = correct_name + domain_name  # Correct name with domain

    # -- Switch section ------------------------------
    log.debug("Entering Switch Section")
    device_dict = {
        "device_type": "autodetect",
        "host": ARGS.switch_ip,
        "username": SSH.username,
        "password": SSH.password
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

    net_connect = ConnectHandler(**device_dict)
    hostname = net_connect.send_command("show version", use_genie=True).get("version", {}).get("hostname")
    if not hostname:
        log.error("Unable to retrieve the hostname of the switch.")
        exit(EXIT_GENERAL_ERROR)
    log.debug(f"Current Hostname: {hostname}")
    if hostname != correct_name:
        log.debug("Mismatch between switch name and correct name.")
        rprint(change_display_table("Switch Name Mismatch", hostname, correct_name))
        if Confirm.ask(f"Would you like to change the switch name to '{correct_name}'?"):
            thread = Thread(target=change_switch_info, args=(net_connect, correct_name, ARGS.building_number, ARGS.room_number))
            thread.start()
        else:
            net_connect.disconnect()  # Disconnect from the switch
            log.debug("Switch connection closed.")

    # -- Orion section ------------------------------
    log.debug("Entering Orion Section")
    orion_data = orion.get_switch(ARGS.switch_ip).get("results")[0]
    log.debug(f"Orion Data: {orion_data}")

    uri = orion_data["URI"]
    node_name = orion_data["NodeName"]

    if node_name != full_name:
        log.debug("Mismatch between switch name and Orion name.")
        rprint(change_display_table("Orion Name Mismatch", node_name, full_name))
        if Confirm.ask(f"Would you like to change the Orion node name to '{correct_name}'?"):
            orion.change_orion_node_name(uri, correct_name)

    log.debug("Exiting Orion Section")

    # -- InfoBlox section ------------------------------
    log.debug("Entering InfoBlox Section")
    ddi_data = ddi_search(ARGS.switch_ip).get("result")
    ddi_names = ddi_data.get("names", "").split(", ")
    for name in ddi_names:
        if name != full_name:
            rprint(change_display_table("InfoBlox Name Mismatch", name, full_name))
            print("There is a mismatch between the switch name and the InfoBlox name. Please fix this manually.")
            print("The current FQHN should be added as an alias for backwards compatibility.")
            rprint(f"The proper switch name for '[green]{ARGS.switch_ip}[/green]' should be: '[green]{correct_name}[/green]' with the domain '[green]{domain_name}[/green]'")
            break

    log.debug("Exiting InfoBlox Section")

    # -- demark section ------------------------------
    log.debug("Entering Demark Section")

    if ARGS.function_descriptor == "dx":
        for alias_number in padder(ARGS.building_number):
            demark_alias = f"dx{ARGS.count}-{alias_number}{domain_name}"
            try:
                demark_ip = gethostbyname(demark_alias)
                log.debug(f"Resolved {demark_alias} to {demark_ip}")
                if demark_ip != ARGS.switch_ip:
                    rprint(
                        f"[green]'{demark_alias}'[/green] resolves to [red]'{demark_ip}'[/red] but should resolve to [green]'{ARGS.switch_ip}'[/green]."
                    )
            except gaierror:
                log.debug(f"Unable to resolve {demark_alias}")
                rprint(f"[green]'{demark_alias}'[/green] also needs to be added.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
