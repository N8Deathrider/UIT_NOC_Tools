#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script performs a device search using the toast.utah.edu API.
It allows users to search for information about a specific device, such as its IP address,
router name, interface, VRF, associated MAC address, switch name, switch IP, port number,
current IP address, port configuration, and port operational information.

The script uses a session-based authentication process to log in to the toast.utah.edu 
website and retrieve the search results.
It also includes functions to format and display the search results in a table format using the rich library.

To use this script, make sure you have the necessary dependencies installed and provide
the required search arguments when calling the 'start_search' function.
"""

# Standard libraries
import json
import logging
from sys import exit
from time import sleep

# Third-party libraries
import requests
from rich import print as rprint
from rich.console import Console
from rich.console import Group
from rich.logging import RichHandler
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

# Local libraries
from u1377551 import login_duo as login
from u1377551 import rich_get_next_arg

# Standard exit codes
EXIT_SUCCESS = 0  # Successful execution
EXIT_GENERAL_ERROR = 1  # General error
EXIT_KEYBOARD_INTERRUPT = 130  # Keyboard interrupt (Ctrl+C)

# Custom exit codes
EXIT_MISSING_ITEM = 2  # User did not provide an item to search for
EXIT_WARNING = 3  # Search returned a warning
EXIT_MAX_RETRIES = 4  # Maximum number of retries reached

# The API url to submit a request to toast
API_SEARCH_URL: str = "https://toast.utah.edu/devicetracker/track"

# The API url to submit the thread ID that was returned from the initial query to retrieve the results of the search
API_THREAD_URL: str = "https://toast.utah.edu/devicetracker/status"


# Setting up the logging
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
log: logging.Logger = logging.getLogger("rich")


def result_formatter(result_data: dict, search_item: str) -> None:
    """
    Formats the search results and prints them to the console.

    Args:
        result_data (dict): The search result data.
        search_item (str): The item being searched for.

    Returns:
        None
    """
    tables = []  # A list to store the tables in
    rf_result: dict[str] = result_data.get("rf_result")  # The result data from the RF (Router Finder) tool
    mt_result: dict[str] = result_data.get("mt_result")  # The result data from the MT (MAC Tracker) tool
    port_operational_info: str | bool = mt_result.get("config") if mt_result else False  # The port operational information from the MT (MAC Tracker) tool

    if rf_result:  # If the RF (Router Finder) tool was able to find a result
        tables.append(
            ip_results_table_gen(
                ip=rf_result.get("current_ip", "xxx.xxx.xxx.xxx"),  #TODO: handle when this is returned but is empty
                router=rf_result.get("name"),  #TODO: figure out what this really is in the result data
                interface=rf_result.get("interface"),
                vrf=rf_result.get("vrf"),
                associated_mac=rf_result.get("mac", "xxxx.xxxx.xxxx")  #TODO: handle when this is returned but is empty
            )
        )

    if mt_result:  # If the MT (MAC Tracker) tool was able to find a result
        tables.append(
            mac_results_table_gen(
                switch_name=mt_result.get("switchname"),
                switch_ip=mt_result.get("switchip"),
                port=mt_result.get("port"),
                current_ip=mt_result.get("current_ip"),
                port_config=mt_result.get("simple_config")
            )
        )

    if port_operational_info:  # If the port operational information was able to be found
        tables.append(
            port_operational_info_table_gen(port_operational_info)
        )

    panel_group = Group(*tables)  # Creating a group of panels to display the tables

    rprint(Panel(
        panel_group,
        border_style="red",
        title=f"[b red]Search Results for:[/b red] [bold white]{search_item}[/bold white]",
        expand=False
    ))  # Printing the group of panels to the terminal


def ip_results_table_gen(ip: str, router: str, interface: str, vrf: str, associated_mac: str) -> Table:
    """
    Generate a table with IP results.

    Args:
        ip (str): The IP address.
        router (str): The router name.
        interface (str): The interface name.
        vrf (str): The VRF (Virtual Routing and Forwarding) name.
        associated_mac (str): The associated MAC (Media Access Control) address.

    Returns:
        Table: The generated table with IP results.
    """
    ip_results_table = Table(
        show_header=True,
        header_style="red",
        title="[bold red]IP Results[/bold red]",
        title_justify="left"
    )
    ip_results_table.add_column("IP")
    ip_results_table.add_column("Router")
    ip_results_table.add_column("Interface")
    ip_results_table.add_column("VRF")
    ip_results_table.add_column("Associated MAC")

    ip_results_table.add_row(
        ip,
        router,
        interface,
        vrf,
        associated_mac,
        style="bold"
    )

    return ip_results_table


def mac_results_table_gen(switch_name: str, switch_ip: str, port: str, current_ip: str, port_config: str) -> Table:
    """
    Generates a table with MAC results.

    Args:
        switch_name (str): The name of the switch.
        switch_ip (str): The IP address of the switch.
        port (str): The port number.
        current_ip (str): The current IP address.
        port_config (str): The port configuration.

    Returns:
        Table: The generated table with MAC results.
    """
    mac_results_table = Table(
        show_header=True,
        header_style="red",
        title="[bold red]MAC Results[/bold red]",
        title_justify="left"
    )
    mac_results_table.add_column("Switch", vertical="middle")
    mac_results_table.add_column("Port", vertical="middle")
    mac_results_table.add_column("Current IP", vertical="middle")
    mac_results_table.add_column("Port config")

    switch_info_table = Table(show_header=False, header_style="red", show_lines=True, expand=True)
    switch_info_table.add_column(style="red")
    switch_info_table.add_column(style="bold")

    switch_info_table.add_row("Switch name", switch_name)
    switch_info_table.add_row("Switch IP", switch_ip)

    mac_results_table.add_row(
        switch_info_table,
        port,
        current_ip,
        port_config,
        style="bold"
    )

    return mac_results_table


def port_operational_info_table_gen(config: str) -> Table:
    """
    Generates a table containing port operational information based on the given configuration.

    Args:
        config (str): The configuration string containing port information.

    Returns:
        Table: The generated table with port operational information.
    """
    port_operational_info_table = Table(
        title="Port Operational Info",
        title_style="bold red",
        show_header=False,
        show_lines=False,
        title_justify="left"
    )
    port_operational_info_table.add_column("Field", style="red", justify="right")
    port_operational_info_table.add_column("Value", style="bold")

    config_items: list[str] = config.replace("\n\n", "\n").splitlines()
    for config_item in config_items:
        if config_item.startswith("Capture Mode"):
            port_operational_info_table.add_row("Capture Mode", config_item.replace("Capture Mode ", ""))
        else:
            port_operational_info_table.add_row(*config_item.split(": "))

    return port_operational_info_table


def status_table_gen(status: dict) -> Table:
    """
    Generate a table displaying the status information.

    Args:
        status (dict): A dictionary containing the status information.

    Returns:
        Table: The generated table.
    """
    status_table = Table(show_header=True, show_lines=True)
    status_table.add_column("Message", style="red", justify="left")
    status_table.add_column("Error", style="Bold")
    status_table.add_column("Warning", style="Bold")
    status_table.add_row(
        status.get("result").get("message"),
        str(status.get("result").get("error")),
        str(status.get("result").get("warning")),
    )
    return status_table


def start_search(s: requests.Session, search_arguments: dict) -> str:
    """
    Sends a GET request to the API search URL with the provided search arguments and returns the result.

    Args:
        s (requests.Session): The requests session object.
        search_arguments (dict): The search arguments to be passed as parameters in the GET request.

    Returns:
        str: The thread ID number returned from the search.
    """
    response: requests.Response = s.get(API_SEARCH_URL, params=search_arguments)
    response.raise_for_status()
    return response.json()["result"]


def check_status(s: requests.Session, status_arguments: dict) -> dict:
    """
    Sends a GET request to the API thread URL with the provided status arguments and returns the result.

    Args:
        s (requests.Session): The requests session object.
        status_arguments (dict): The status arguments to be passed as parameters in the GET request.

    Returns:
        dict: The status information returned from the search.
    """
    response: requests.Response = s.get(API_THREAD_URL, params=status_arguments)
    response.raise_for_status()
    return response.json()


def main_v1():
    from sys import argv
    # This is imported here to get rid of a waring about this not being
    # imported even though it is not used in V2 so it is not imported globally

    i = 0  # The number of times the script has searched for the thread ID
    retries = 25  # The number of times the script will search for the thread ID before giving up
    api_search_url = 'https://toast.utah.edu/devicetracker/track' # The API url to submit a request to toast
    api_thread_url = 'https://toast.utah.edu/devicetracker/status' # The API url to submit the thread ID that was returned from the initial query to retrieve the results of the search

    if len(argv) < 2:  # Checking if the user has provided an item to search for
        item = Prompt.ask("What would you like to look for?")  # If not asking them for one
        # item = "test2"  # DEBUG
    else:  # If they have provided an item to search for
        item = argv[1]  # Storing it as a variable
    # item = str("155.99.254.243") #DEBUG


    if item == "test":  # DEBUG
        test_json_object = {
            "result": {
                "message": None,
                "data": {
                    "rf_result": {
                        "ip": "155.99.254.243",
                        "vrf": None,
                        "interface": "Vlan299",
                        "name": "r2-wifi-park",
                        "config": "!Command: show running-config interface Vlan299\r\n!Time: Fri Apr 28 08:28:49 2023\r\n\r\nversion 8.2(2)\r\n\r\ninterface Vlan299\r\n  description #wifi-netops-UConnect\r\n  no shutdown\r\n  no ip redirects\r\n  ip address 155.99.254.131/25\r\n  ipv6 address 2604:c340:2000:254::3/64\r\n  ipv6 nd other-config-flag\r\n  no ipv6 redirects\r\n  ip ospf passive-interface\r\n  ip router ospf 1 area 0.0.0.0\r\n  ospfv3 passive-interface\r\n  ipv6 router ospfv3 1 area 0.0.0.0\r\n  ip pim sparse-mode\r\n  hsrp version 2\r\n  hsrp 299 \r\n    authentication md5 key-chain hsrp\r\n    ip 155.99.254.129\r\n  hsrp 299 ipv6\r\n    authentication md5 key-chain hsrp\r\n    ip 2604:c340:2000:254::1\r\n  ip dhcp relay address 155.97.186.76 \r\n  ip dhcp relay address 10.72.2.148 \r\n  ip dhcp relay address 10.72.2.149 \r\n  ip dhcp relay address 10.72.2.152 \r\n  ip dhcp relay address 10.72.62.12 \r\n  ipv6 dhcp relay address 2604:c340:dd1:706::152\r\n\r",
                        "ip2": "155.99.130.68",
                        "name2": "r1-wifi-ebc",
                        "config2": "!Command: show running-config interface Vlan299\r\n!Time: Fri Apr 28 08:28:52 2023\r\n\r\nversion 8.2(2)\r\n\r\ninterface Vlan299\r\n  description #wifi-netops-UConnect\r\n  no shutdown\r\n  no ip redirects\r\n  ip address 155.99.254.130/25\r\n  ipv6 address 2604:c340:2000:254::2/64\r\n  ipv6 nd other-config-flag\r\n  no ipv6 redirects\r\n  ip ospf passive-interface\r\n  ip router ospf 1 area 0.0.0.0\r\n  ospfv3 passive-interface\r\n  ipv6 router ospfv3 1 area 0.0.0.0\r\n  ip pim sparse-mode\r\n  hsrp version 2\r\n  hsrp 299 \r\n    authentication md5 key-chain hsrp\r\n    preempt delay minimum 300 \r\n    priority 254\r\n    ip 155.99.254.129\r\n  hsrp 299 ipv6\r\n    authentication md5 key-chain hsrp\r\n    preempt delay minimum 300 \r\n    priority 254\r\n    ip 2604:c340:2000:254::1\r\n  ip dhcp relay address 155.97.186.76 \r\n  ip dhcp relay address 10.72.2.148 \r\n  ip dhcp relay address 10.72.2.149 \r\n  ip dhcp relay address 10.72.2.152 \r\n  ip dhcp relay address 10.72.62.12 \r\n  ipv6 dhcp relay address 2604:c340:dd1:706::152\r\n\r",
                        "mac": "d457.63d8.2c3a",
                        "current_ip": "155.99.254.243"
                    },
                    "mt_result": {
                        "switchname": "wlc-ha-6",
                        "switchip": "172.28.3.56",
                        "port": None,
                        "message": "The CDP Port that this device is connected to could not be found. Here is the last known information.",
                        "simple_config": None,
                        "config": None,
                        "current_ip": "155.99.254.243"
                    }
                },
                "error": False,
                "warning": False
            }
        }
        result_formatter(result_data=test_json_object["result"]["data"], search_item=item)
        exit()
    elif item == "test2":  # DEBUG
        test_json_object = {
            "result": {
                "message": None,
                "data": {
                    "rf_result": None,
                    "mt_result": {
                        "switchname": "sx1-0482-102tower-5th-test",
                        "switchip": "172.31.16.52",
                        "port": "Gi0/9",
                        "message": None,
                        "simple_config": "Building configuration...\r\n\r\nCurrent configuration : 126 bytes\r\n!\r\ninterface GigabitEthernet0/9\r\n switchport access vlan 986\r\n switchport mode access\r\n no keepalive\r\n spanning-tree portfast\r\nend\r\n\r",
                        "config": "Name: Gi0/9\nSwitchport: Enabled\nAdministrative Mode: static access\nOperational Mode: static access\nAdministrative Trunking Encapsulation: dot1q\nOperational Trunking Encapsulation: native\nNegotiation of Trunking: Off\nAccess Mode VLAN: 986 (noc-wrkstns-inside)\nTrunking Native Mode VLAN: 1 (default)\nAdministrative Native VLAN tagging: enabled\nVoice VLAN: none\nOperational private-vlan: none\nTrunking VLANs Enabled: ALL\nPruning VLANs Enabled: 2-1001\nCapture Mode Disabled\nCapture VLANs Allowed: ALL\n\nProtected: false\nUnknown unicast blocked: disabled\nUnknown multicast blocked: disabled\nAppliance trust: none",
                        "current_ip": "172.20.120.20"
                    }
                },
                "error": None,
                "warning": None
            }
        }
        result_formatter(result_data=test_json_object["result"]["data"], search_item=item)
        exit()
    elif item == "test3":  # DEBUG
        test_json_object = {
            "result": {
                "message": None,
                "data": {
                    "rf_result": {
                        "ip": "172.31.10.107",
                        "vrf": None,
                        "interface": "Vlan153",
                        "name": "r1-482-102tower-2940b",
                        "config": "Building configuration...\r\n\r\nCurrent configuration : 277 bytes\r\n!\r\ninterface Vlan153\r\n description 102tower-floor5-voip\r\n ip address 172.22.181.1 255.255.255.0\r\n ip helper-address 155.101.246.200\r\n ip helper-address 155.97.136.200\r\n no ip redirects\r\n no ip unreachables\r\n no ip proxy-arp\r\n ip flow monitor NETFLOW output\r\n ip ospf 1 area 0.0.0.0\r\nend\r\n\r",
                        "ip2": None,
                        "name2": "",
                        "config2": None,
                        "mac": "4825.6746.347a",
                        "current_ip": "172.22.181.24"
                    },
                    "mt_result": {
                        "switchname": "sx1-482-102tower-5w-4401-102tower",
                        "switchip": "172.31.16.14",
                        "port": "GigabitEthernet3/16",
                        "message": None,
                        "simple_config": "Building configuration...\r\n\r\nCurrent configuration : 169 bytes\r\n!\r\ninterface GigabitEthernet3/16\r\n description Desk 5365 Phone\r\n switchport access vlan 151\r\n switchport mode access\r\n switchport voice vlan 153\r\n spanning-tree portfast\r\nend\r\n\r",
                        "config": "Name: Gi3/16\nSwitchport: Enabled\nAdministrative Mode: static access\nOperational Mode: static access\nAdministrative Trunking Encapsulation: dot1q\nOperational Trunking Encapsulation: native\nNegotiation of Trunking: Off\nAccess Mode VLAN: 151 (102tower-floor5-campus)\nTrunking Native Mode VLAN: 1 (default)\nAdministrative Native VLAN tagging: enabled\nVoice VLAN: 153 (102tower-floor5-voip)\nOperational private-vlan: none\nTrunking VLANs Enabled: ALL\nPruning VLANs Enabled: 2-1001\nCapture Mode Disabled\nCapture VLANs Allowed: ALL\n\nUnknown unicast blocked: disabled\nUnknown multicast blocked: disabled\nAppliance trust: none",
                        "current_ip": "172.22.181.24"
                    }
                },
                "error": False,
                "warning": False
            }
        }
        result_formatter(result_data=test_json_object["result"]["data"], search_item=item)
        exit()

    s: requests.Session = login()  # Creating the session and logging in

    print('Beginning the search for your answers!') # To let you know the search has started

    search_arguments = {'search_item': item, 'mac_only': False, 'ip_only': False, 'get_config': True} # Organizing the search items to pretty up the request

    r: requests.Response = s.get(api_search_url, params=search_arguments) # The actual first request sending the search information to toast

    if r.ok == True: # Checking for a 200 web response and breaking after printing an error code if not
        result = r.json()['result'] # Isolating the returned thread ID number and storing it as a variable
    else:  # If the request was not successful
        exit(f"Error:\n {r.text} \n URL:\n {r.url}")  # Printing the error message to the terminal and exiting the program with an error code

    status_arguments = {'thread_id': result}  # Adding the just returned thread ID number to the parameter that will be used in the request to get back the information toast was able to find

    while i < retries:  # Looping until the max number of searches is reached
        r2 = s.get(api_thread_url, verify=False, params=status_arguments) # request for the results from toast using the thread ID and with every loop storing the data in the variable to keep it fresh
        if r2.ok == True and r2.json()['result']['data'] != None: # Checking for a 200 status code and that the "data" field in the returned json is not None like in the even of toast just giving an update message
            json_object = json.loads(r2.content)  # The current way I am using to pretty up the json
            try:  # Trying to format the results and print them to the terminal
                print("\033[2F", end="")  # Move the cursor up 2 lines
                result_formatter(result_data=json_object["result"]["data"], search_item=item) # Calling the function that will format and print the results
            except Exception as e:  # Catching any errors that might occur and printing the json to the terminal to help with debugging
                print(e)  # Printing the error message to the terminal
                print(json.dumps(json_object, indent=4))  # Printing the json to the terminal
                exit(1)  # Exiting the program with an error code
            exit() # To end the program after a successful run
        elif r2.ok == True and r2.json()["result"]["warning"]:  # Checking for a 200 status code and that the "warning" field in the returned json is not None like in the even of toast just giving an update message
            warning_message = r2.json()['result']['message']
            rprint(f"[red][!][/red] [bold yellow][u]{item}[/u] - {warning_message}[/bold yellow]")
            exit()  # Exiting the program with an error code
        else:  # If the request was not successful
            rprint(r2.json())  # Printing the json to the terminal
            i += 1 # Increment the search iteration number by one
            sleep(5) # Waiting for 5 seconds to not flood toast with request and to also attempt to reduce the number of request attempts before a success
    else:  # If the number of searches reaches the max number allowed
        exit('Error: Script has tried ' + str(retries) + ' times and will now exit.')  # Printing an error message to the terminal and exiting the program with an error code


def main_v2(max_retries: int = 25):
    """
    Perform a search for a specified item and retrieve results.

    Args:
        max_retries (int): The maximum number of times the script will search for the thread ID before giving up.

    Returns:
        None
    """

    # Creating a console object
    console = Console()

    # The number of times the script has searched for the thread ID
    times_searched: int = 0

    # The number of times the script will search for the thread ID before giving up
    MAX_RETRIES: int = max_retries

    # Getting the item to search for
    item = rich_get_next_arg("What would you like to look for?")

    # Checking if the user has provided an item to search for
    if not item:
        log.warning("No search item provided. Exiting.")
        exit(EXIT_MISSING_ITEM)

    # Creating the session and logging in
    s: requests.Session = login()
    log.debug("Session created and logged in.")

    # Setting up the search arguments
    SEARCH_ARGUMENTS: dict[str, str] = {"search_item": item, "mac_only": False, "ip_only": False, "get_config": True}
    log.debug(f"Search arguments created. {SEARCH_ARGUMENTS=}")

    # Starting the search
    try:
        STATUS_ARGUMENTS: dict[str, str] = {"thread_id": start_search(s, SEARCH_ARGUMENTS)}
    except requests.exceptions.HTTPError as e:
        log.error(f"{e.response.json().get('error')}")
        exit(EXIT_GENERAL_ERROR)
    except Exception as e:
        log.exception(f"An error occurred while starting the search. {e}")
        exit(EXIT_GENERAL_ERROR)
    log.debug(f"Search started. {STATUS_ARGUMENTS=}")

    # Checking the status of the search
    with console.status("[bold red]Searching for results...") as status:

        # Looping until the max number of searches is reached
        while times_searched < MAX_RETRIES:

            # Getting the status of the search
            response_json: dict = check_status(s, STATUS_ARGUMENTS)

            # Checking if the search was successful
            if response_json["result"]["data"]:  # If the search was successful
                status.stop()
                result_formatter(response_json["result"]["data"], item)
                exit(EXIT_SUCCESS)
            elif response_json["result"]["warning"]:  # If the search returned a warning
                status.stop()
                log.warning(f"{item} - {response_json['result']['message']}")
                exit(EXIT_WARNING)
            else:  # If the search was not successful and did not return a warning
                times_searched += 1
                sleep(5)
                log.debug(f"Search attempt {times_searched} failed. Trying again.")

        else:  # If the number of searches reaches the max number allowed
            log.error(f"Script has tried {times_searched} times out of a max {MAX_RETRIES} and will now exit.")
            exit(EXIT_MAX_RETRIES)


if __name__ == "__main__":
    try:  # Try to run the main function
        main_v2()
    except KeyboardInterrupt:  # If the user interrupts the script with a keyboard interrupt
        log.warning("Exiting due to keyboard interrupt.")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:  # If an unhandled exception occurs
        log.exception(f"An unhandled exception occurred. {e}")
        exit(EXIT_GENERAL_ERROR)

