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
from uit_duo import Duo
from u1377551 import rich_get_next_arg

try:
    from auth import UofU

    uNID = UofU.unid
    password = UofU.cisPassword
except ImportError:
    from getpass import getpass

    uNID = input("Enter your uNID: ")
    password = getpass("Enter your: cis password: ")

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
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        log.error(f"{e.response.json().get('error')}")
        exit(EXIT_GENERAL_ERROR)
    return response.json()


def main(max_retries: int = 25):
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
    duo = Duo(uNID=uNID, password=password)
    s: requests.Session = duo.login()
    requests.urllib3.disable_warnings()
    s.verify = False
    s.get("https://toast.utah.edu/login_helper")
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
        main()
    except KeyboardInterrupt:  # If the user interrupts the script with a keyboard interrupt
        log.warning("Exiting due to keyboard interrupt.")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:  # If an unhandled exception occurs
        log.exception(f"An unhandled exception occurred. {e}")
        exit(EXIT_GENERAL_ERROR)
