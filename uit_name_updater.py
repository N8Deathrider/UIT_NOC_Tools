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
import re
from bs4 import BeautifulSoup
from sys import exit
import webbrowser  # TODO: Evaluate if this is needed
from socket import gethostbyname
from socket import gaierror
from time import sleep
import urllib3
from threading import Thread

# Third-party libraries
import requests
from rich_argparse import RichHelpFormatter
from rich.console import Console
from rich.logging import RichHandler
from rich.prompt import Confirm
from rich.table import Table
from rich import print as rprint
from uit_duo import Duo, get_form_args
from netmiko import ConnectHandler, SSHDetect, BaseConnection
from netmiko import NetmikoAuthenticationException, NetmikoTimeoutException, ConfigInvalidException
import orionsdk
from playwright.sync_api import Playwright, sync_playwright, expect
from yarl import URL

# Local libraries


# Standard exit codes
EXIT_SUCCESS = 0  # No errors
EXIT_GENERAL_ERROR = 1  # General error
EXIT_INVALID_ARGUMENT = 120  # Invalid argument to exit
EXIT_KEYBOARD_INTERRUPT = 130  # Keyboard interrupt (Ctrl+C)

CONSOLE = Console()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=CONSOLE)],
)
log: logging.Logger = logging.getLogger("rich")
logging.getLogger("paramiko").setLevel(logging.WARNING)  # Suppress Paramiko info logs


try:
    from auth import UofU, SSH

    ORION_USERNAME, ORION_PASSWORD = f"ad\\{UofU.unid}", UofU.cisPassword
except ImportError:
    print("No auth.py file found.")
    from getpass import getpass
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
    class UofU:
        unid = uNID
        cisPassword = ORION_PASSWORD


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


def remove_duplicates(lst: list) -> list:
    """
    Removes duplicates from a list while preserving the order of the elements.

    Args:
        lst (list): The list to remove duplicates from.

    Returns:
        list: The list with duplicates removed.
    """
    res = []
    [res.append(x) for x in lst if x not in res]
    return res


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
        "current standards and updates it in the needed places.",
        formatter_class=RichHelpFormatter,
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
        "--log-level",
        type=str,
        default="error",
        choices=["debug", "info", "warning", "error", "critical"],
        help=argparse.SUPPRESS
    )

    return parser.parse_args()


def get_switch_name(connection: BaseConnection) -> str:
    """
    Get the current hostname of the switch.

    Args:
        connection (BaseConnection): The connection object used to communicate with the switch.

    Returns:
        str: The current hostname of the switch.
    """
    return connection.send_command("show version", use_genie=True).get("version", {}).get("hostname")


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


def dns_change_allowed_checker(results: dict) -> str | None:
    """
    Checks if DNS change is allowed based on the provided results.

    Args:
        results (dict): The dictionary containing the results.

    Returns:
        str | None: The host record if DNS change is allowed, otherwise None.
    """
    objects = results.get("objects") or results["result"]["objects"]
    joined_objects = "".join(objects)
    host_record_count = joined_objects.count("record:host")

    if host_record_count < 1:
        log.warning("No host records found.")
        return None
    elif host_record_count > 1:
        log.warning("Multiple host records found.")
        return None

    if "External" in joined_objects:
        log.warning("External host record found.")
        return None

    for obj in objects:
        if obj.startswith("record:host"):
            return obj.split(":")[2].split("/")[0]


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


def demark_alias_generator(building_number: str, switch_count: str, ip_address: str) -> list[str]:
    """
    Generates a list of demark aliases for a given building when they do not exist already.

    Args:
        building_number (str): The building number.
        switch_count (str): The switch count.
        ip_address (str): The IP address.

    Returns:
        list[str]: A list of demark aliases.

    Raises:
        None
    """


    demark_aliases = []
    building_numbers = []
    building_number = str(int(building_number))  # Convert the building number to an integer and then back to a string to remove leading 0's
    for number in range(5):
        building_numbers.append(building_number.zfill(number))
    building_numbers = remove_duplicates(building_numbers)

    for building_number in building_numbers:
        demark_alias = f"dx{switch_count}-{building_number}.net.utah.edu"
        try:
            demark_ip = gethostbyname(demark_alias)
            log.debug(f"Resolved {demark_alias} to {demark_ip}")
            if demark_ip != ip_address:
                log.warning(f"'{demark_alias}' resolves to '{demark_ip}' but should resolve to '{ip_address}'.")
        except gaierror:
            log.debug(f"Unable to resolve {demark_alias}")
            demark_aliases.append(demark_alias)

    return demark_aliases


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


def dns_changer_playwright(
    playwright: Playwright,
    ip_address: str,
    desired_dns: str,
    current_dns: str,
    aliases: list[str] = [],
    headless: bool = True
) -> None:
    log.debug("Opening InfoBlox in Playwright")
    log.debug(f"Current DNS: '{current_dns}' Desired DNS: '{desired_dns}' Aliases: '{aliases}'")
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context()  # TODO: add logic for saving and reusing session info
    page = context.new_page()
    current_dns = current_dns.removesuffix(".net.utah.edu")  # Remove the domain from the current DNS
    if current_dns not in aliases:  # If the current DNS is not in the aliases list
        aliases.append(current_dns)  # Add the current DNS to the aliases list
        log.debug(f"Added current DNS to aliases: {current_dns}")
    aliases = remove_duplicates(aliases)  # Remove duplicates from the aliases list
    page.goto("https://ddi.utah.edu/ui/")

    # Login
    page.get_by_label("Username").fill(UofU.unid)
    page.get_by_label("Password").fill(UofU.cisPassword)
    page.get_by_role("button", name="Login").click()

    # Search for IP
    page.get_by_role("link", name="Search").click()
    page.get_by_role("link", name="Advanced").click()
    page.locator(
        'input[name="contentsPanelID\\:panel\\:emtabpanel\\:panel\\:lazyContent\\:content\\:filterPanel\\:filterForm\\:searchTextField"]'
    ).fill(f"{ip_address}$")  # Setting end of regex to match only the IP address
    page.locator(
        'select[name="contentsPanelID\\:panel\\:emtabpanel\\:panel\\:lazyContent\\:content\\:filterPanel\\:filterForm\\:filters\\:1\\:userFilter\\:valueDropDownWidget"]'
    ).select_option("63")
    page.get_by_role("button", name="Search").click()

    # Select correct record
    page.get_by_text(f"Internal/{current_dns}.net.utah.edu").click()

    # Get current name
    old_dns = page.get_by_label("Name").input_value()
    assert old_dns == current_dns, f"Old DNS: {old_dns}\nCurrent DNS: {current_dns}"  # Should be the same as current_dns

    # Update DNS
    page.get_by_label("Name").fill(desired_dns.removesuffix(".net.utah.edu"))

    # Save changes
    page.get_by_role("button", name="Save & Close").click()
    sleep(1)  # Wait for save to complete
    try:  # Check for error message
        expect(page.get_by_text("Operation not possible due to uniqueness constraint")).to_be_hidden()
        expect(page.get_by_text("Missing value for extensible attribute 'Device Type'.")).to_be_hidden()
    except AssertionError:  # If error message is present, print message and close browser
        print("Error encountered saving new name, please resolve manually.")
        context.close()
        browser.close()

    # Select correct record again
    page.get_by_text(f"Internal/{current_dns}.net.utah.edu").click()

    # Select Aliases tab
    page.get_by_role("link", name="Aliases").click()

    # Add aliases
    for alias in aliases:
        if page.locator("div.ib-inner.ib-ur-host-editor em.x-unselectable > button.ib_h_icon_add").count() > 1:
            sleep(1)  # Wait for the duplicate button to be removed
        page.locator("div.ib-inner.ib-ur-host-editor em.x-unselectable > button.ib_h_icon_add").click()
        sleep(1)  # Wait for the new row to be added and ready for input
        page.locator("div.ib-ur-host-editor div.x-grid3-row-last").click()  # Click on the new row to reveal the input field
        page.locator("div.ib-ur-host-editor input.x-form-field").last.fill(alias)  # Fill in the alias
        page.locator("div.ib-ur-host-editor input.x-form-field").last.press("Enter")  # Press enter to save the alias

    # Save changes
    page.get_by_role("button", name="Save & Close").click()
    sleep(1)  # Wait for save to complete
    try:  # Check for error message
        expect(page.get_by_text("Operation not possible due to uniqueness constraint")).to_be_hidden()
        expect(page.get_by_text("Missing value for extensible attribute 'Device Type'.")).to_be_hidden()
    except AssertionError:  # If error message is present, print message and close browser
        print("Error encountered adding aliases, please resolve manually.")
        context.close()
        browser.close()
        print(f"Aliases that should be added: {','.join(aliases)}")

    # ---------------------
    context.close()
    browser.close()


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


def change_display_table(table_title: str, current_name: str, proposed_name: str):
    """
    Creates a display table with the given table title, current name, and proposed name.

    Args:
        table_title (str): The title of the table.
        current_name (str): The current name.
        proposed_name (str): The proposed name.

    Returns:
        Table: The display table with the title, current name, and proposed name.
    """
    table = Table(title=table_title, show_header=False, style="red")

    table.add_row("[bold]Current Name:", current_name)
    table.add_row("[bold]Proposed Name:", proposed_name)

    return table


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
    try:
        switch_output += connection.send_config_set(
            commands,
            error_pattern=r"(Invalid input detected at|Command authorization failed)",
        )
    except ValueError as e:
        log.error(e)
    except ConfigInvalidException as e:
        log.error(e)
        print("-" * 80)
        print("\n".join([cmd.replace("\n", "") for cmd in commands]))
        print("-" * 80)
    else:
        connection.set_base_prompt()
        switch_output += connection.save_config()
        log.debug(f"Output: {switch_output}")
    finally:
        connection.disconnect()  # Disconnect from the switch
        log.debug("Switch connection closed.")


def create_ticket(dns_ip: str, dns_pop_ip: str, dns_fqhn: str, dns_pop_fqhn: str) -> None:
    """
    Creates a ticket in ServiceNow for the switch name change.

    Args:
    - dns_ip (str): The current IP address of the DNS record.
    - dns_pop_ip (str): The proposed IP address of the DNS record.
    - dns_fqhn (str): The current fully qualified host name of the DNS record.
    - dns_pop_fqhn (str): The proposed fully qualified host name of the DNS record.

    Returns:
    None
    """

    base_url = URL("https://uofu.service-now.com/")

    # sys_id for the DNS Update Request catalog item
    sys_id = "a7abab2913c28340af4150782244b0c3"

    duo = Duo(uNID=UofU.unid, password=UofU.cisPassword)

    session: requests.Session = duo.login()

    response: requests.Response = session.get(base_url, allow_redirects=True)

    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        log.error(f"HTTP Error: {e}")

    sysparm_url = URL(response.url).query.get("sysparm_url")

    response: requests.Response = session.get(sysparm_url, allow_redirects=True)

    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        log.error(f"HTTP Error: {e}")

    saml_response = get_form_args(response.text, "SAMLResponse")
    # TODO: Add error handling for when the SAMLResponse is not found

    response: requests.Response = session.post(base_url / "navpage.do", data={"SAMLResponse": saml_response})

    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        log.error(f"HTTP Error: {e}")

    response: requests.Response = session.get(base_url / "it", params={"id": "uu_catalog_item", "sys_id": sys_id})

    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        log.error(f"HTTP Error: {e}")

    reg = re.compile(r"window\.g_ck = '(.*?)'")

    match = reg.search(response.text)
    # TODO: Add error handling for when the regex doesn't match

    # The X-Usertoken header is required to access the ServiceNow API
    session.headers.update({"X-Usertoken": match.group(1)})

    response: requests.Response = session.get(base_url / "api/now/sp/page", params={"id": "uu_catalog_item", "sys_id": sys_id})

    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        log.error(f"HTTP Error: {e}")

    user_info = response.json()["result"]["user"]

    response: requests.Response = session.post(
        base_url / "api/sn_sc/v1/servicecatalog/items" / sys_id / "order_now",
        json={
            "sysparm_quantity": "1",
            "variables": {
                "requester": user_info["sys_id"],
                "requester_phone": user_info["phone"],
                "requester_vs": "true",  # TODO: Figure out what this is and if it needs to be dynamic
                "addl_info_vs": "",
                "requester_unid": user_info["user_name"],
                "dns_prop_fqhn": dns_pop_fqhn,
                "addl_info_label": "",
                "addl_info": "The current FQHN will be added as an alias for backwards compatibility.",
                "dns_prop_ip": dns_pop_ip,
                "requester_email": user_info["email"],
                "dns_fqhn": dns_fqhn,
                "requester_info_label": "",
                "requester_department": user_info["department"],
                "dns_ip": dns_ip,
                "dns_mac": "",
                "dns_req_type": "dns_update",
                "requester_cont_start": "true",
            },
            "sysparm_item_guid": sys_id,
            "get_portal_messages": "true",
            "sysparm_no_validation": "true",
        },
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        log.error(f"HTTP Error: {e}")

    log.debug(f"Response: {response.json()}")
    if response.ok:
        log.debug("Ticket created successfully.")
    else:
        log.error("Ticket creation failed.")
        return False

    log.debug("Searching for new ticket.")
    request_ticket_ref = response.json()["result"]["request_number"]

    # This is because after creating the REQ ticket, it takes some time for the RITM and the TASK to be created
    for _ in range(20):
        response: requests.Response = session.get(
            base_url / "api/now/v2/table/task",
            params={
                "sysparm_query": f"123TEXTQUERY321={request_ticket_ref}^numberSTARTSWITHTASK"
            },
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            log.error(f"HTTP Error: {e}")

        if len(response.json()["result"]) > 0:
            break
        else:
            sleep(2)
    else:
        log.error("Ticket not found after 20 search attempts. Ticket should be sitting in the DDI queue. Please take the ticket.")
        return False

    try:
        task_id = response.json()["result"][0]["sys_id"]
    except Exception:
        log.error("Error")
        with open("ticket.json", "w") as f:
            f.write(response.text)
        return False
    log.debug(f"Task ID: {task_id}")

    response: requests.Response = session.get(
        base_url / "sc_task.do",
        params={"sys_id": task_id},
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        log.error(f"HTTP Error: {e}")

    log.debug("Attempting to reassign ticket.")

    response: requests.Response = session.post(
        base_url / "sc_task.do",
        data={
            "sysparm_ck": get_form_args(response.text, "sysparm_ck"),
            "sys_target": "sc_task",
            "sys_uniqueName": "sys_id",
            "sys_uniqueValue": task_id,  # This is the sys_id of the ticket
            "sys_action": "47fd7f4dc0a8000600a552278b5232ab",  # Looks to be the same for each ticket
            "sc_task.state": "2",  # Work in Progress
            # "sc_task.state": "3",  # Closed Complete
            "sc_task.assignment_group": "d4bb465a6f6a1100c62f8a20af3ee4a9",  # This is the id for UIT - NCI - Network
            "sc_task.assigned_to": user_info["sys_id"],  # Assign the ticket to the requester
        },
        allow_redirects=False,
    )

    if response.status_code == 302 and task_id in response.headers["Location"]:
        log.debug("Ticket reassigned successfully.")
        return True
    else:
        log.error("Ticket reassignment failed. Ticket should be sitting in the DDI queue.  Please take the ticket.")
        log.debug(f"Redirect URL: {response.headers['Location']}\nStatus Code: {response.status_code}")
        return 


def ddi_name_change(ip_address: str, correct_name: str, current_name: str, aliases: list[str] = []) -> None:
    with sync_playwright() as p:
        dns_changer_playwright(p, ip_address, correct_name, current_name, aliases)
        
    # Checking if the DNS change was successful
    ddi_data = ddi_search(ip_address).get("result")
    if f"{correct_name}.net.utah.edu" in ddi_data.get("names", "").split(", "):
        print("DNS change successful.")
    else:
        log.error("DNS change check failed. Please verify the DNS change manually.")


def main() -> None:
    """
    #TODO
    """

    threads = []  # List to hold the threads
    orion = Orion("smg-hamp-p01.ad.utah.edu", ORION_USERNAME, ORION_PASSWORD)

    ARGS = get_args()

    match ARGS.log_level:
        case "debug":
            log.setLevel(logging.DEBUG)
        case "info":
            log.setLevel(logging.INFO)
        case "warning":
            log.setLevel(logging.WARNING)
        case "error":
            log.setLevel(logging.ERROR)
        case "critical":
            log.setLevel(logging.CRITICAL)
        case _:  # Default to WARNING
            log.setLevel(logging.WARNING)

    log.debug(f"Arguments: {ARGS}")

    # Generating the correct name
    with CONSOLE.status("Gathering Information...") as status:
        status.update("Generating Correct Name...")
        correct_name = name_generator(
            ARGS.function_descriptor,
            ARGS.count,
            ARGS.building_number,
            ARGS.building_short_name,
            ARGS.room_number,
            ARGS.distribution_node,
        )
        domain_name = ".net.utah.edu"
        full_name = correct_name + domain_name  # Correct name with domain

        # Getting the switch connection
        status.update("Connecting to Switch...")
        switch_connection_dict = {
            "device_type": "autodetect",
            "host": ARGS.switch_ip,
            "username": SSH.username,
            "password": SSH.password,
        }
        try:
            guesser = SSHDetect(**switch_connection_dict)
        except NetmikoAuthenticationException:
            log.error("Authentication error. Please check the username and password.")
            exit(EXIT_GENERAL_ERROR)
        except NetmikoTimeoutException:
            log.error("Connection timed out. Please check the IP address and try again.")
            exit(EXIT_GENERAL_ERROR)
        best_match = guesser.autodetect()
        switch_connection_dict["device_type"] = best_match
        if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
            dev_device_dict = switch_connection_dict.copy()
            dev_device_dict["password"] = "********"
            log.debug(f"Device dictionary: {dev_device_dict}")
            del dev_device_dict
        switch_connection = ConnectHandler(**switch_connection_dict)

        # Getting the current switch name
        status.update("Getting Current Switch Name...")
        current_switch_name = get_switch_name(switch_connection)
        log.debug(f"Current Switch Name: {current_switch_name}")

        # Getting Orion data
        status.update("Getting Orion Data...")
        orion_data = orion.get_switch(ARGS.switch_ip).get("results")[0]
        log.debug(f"Orion Data: {orion_data}")

        uri = orion_data["URI"]
        node_name = orion_data["NodeName"]

        # Getting InfoBlox data
        status.update("Getting InfoBlox Data...")
        ddi_data = ddi_search(ARGS.switch_ip).get("result")

        # Check if DNS change is allowed
        ddi_name = dns_change_allowed_checker(ddi_data)

        # Get the dns names
        ddi_names = ddi_data.get("names", "").split(", ")

        if ddi_name:
            log.debug(f"Host Record DNS Name: {ddi_name}")
        else:
            log.debug(f"Automatic DNS Change Not Allowed, Manual Change Required. First DNS Name Found: {ddi_names[0]}")

        # Get the aliases
        if ARGS.function_descriptor == "dx":
            aliases = demark_alias_generator(
                ARGS.building_number, ARGS.count, ARGS.switch_ip
            )
        else:
            aliases = []
        log.debug(f"Aliases: {aliases}")

    # Prompt to change switch name if necessary
    if current_switch_name != correct_name:
        log.debug("Mismatch between switch name and correct name.")

        # Display the mismatch
        rprint(change_display_table("Switch Name Mismatch", current_switch_name, correct_name))

        # Prompt to change the switch name
        if Confirm.ask(f"Would you like to change the switch name to '{correct_name}'?"):
            switch_thread = Thread(
                target=change_switch_info,
                args=(
                    switch_connection,
                    correct_name,
                    ARGS.building_number,
                    ARGS.room_number,
                ),
            )
            threads.append(switch_thread)
            log.debug(f"Threads: {threads}")
            switch_thread.start()
        else:
            log.debug("Switch name will not be changed. Disconnecting from switch.")
            switch_connection.disconnect()
    else:
        log.debug("Switch name matches correct name. Disconnecting from switch.")
        switch_connection.disconnect()

    # Prompt to change Orion node name if necessary
    if node_name != full_name:
        log.debug("Mismatch between switch name and Orion name.")

        # Display the mismatch
        rprint(change_display_table("Orion Name Mismatch", node_name, full_name))

        # Prompt to change the Orion node name
        if Confirm.ask(f"Would you like to change the Orion node name to '{correct_name}'?"):
            orion_thread = Thread(
                target=orion.change_orion_node_name,
                args=(uri, correct_name),
            )
            threads.append(orion_thread)
            log.debug(f"Threads: {threads}")
            orion_thread.start()

    # Prompt to change InfoBlox name if necessary
    if full_name not in ddi_names:
        log.debug("Mismatch between switch name and InfoBlox name.")

        # Display the mismatch
        rprint(change_display_table("InfoBlox Name Mismatch", ddi_name or ddi_names[0], full_name))

        # Check if the DNS name can be changed and if so, offer to try automatically changing it
        # If the ddi_name is None meaning the DNS change is not allowed, the user will have to change it manually
        # and should not be prompted to try automatically changing it
        if ddi_name and Confirm.ask(f"Would you like to try automatically changing the DNS?"):
            ddi_thread = Thread(
                target=ddi_name_change,
                args=(ARGS.switch_ip, correct_name, ddi_name, aliases),
            )
            threads.append(ddi_thread)
            log.debug(f"Threads: {threads}")
            ddi_thread.start()
        else:  # If the DNS name cannot be changed automatically or the user chooses not to
            log.debug("DNS name will not be changed automatically.")
            rprint(
                f"The proper switch name for '{ARGS.switch_ip}' should be: '{correct_name}' with the domain '{domain_name}' and the aliases: '{'\', \''.join(aliases)}'"
            )

        # Prompt to create a ticket for the DNS change
        if Confirm.ask("Would you like a ticket to be created for this change?", default=True):
            if create_ticket(ARGS.switch_ip, ARGS.switch_ip, ddi_name or ddi_names[0], full_name):
                print("Ticket created successfully.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
