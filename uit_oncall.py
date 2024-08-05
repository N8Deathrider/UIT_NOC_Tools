#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script retrieves on-call information from a specified URL and displays it in a table format.

The script uses Duo authentication to log in and create a session. It then sends a GET request to the specified URL
to retrieve the on-call information. The retrieved information is displayed in a table using the rich library.

The script requires the following dependencies:
- requests
- rich
"""

# Standard libraries
import logging
from sys import exit

# Third-party libraries
import requests
from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler

# Local libraries
from uit_duo import Duo

try:
    from auth import UofU

    uNID = UofU.unid
    password = UofU.cisPassword
except ImportError:
    from getpass import getpass

    uNID = input("Enter your uNID: ")
    password = getpass("Enter your: cis password: ")

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


def table_maker(oncall: list) -> Table:
    """
    Create a table with on-call information.

    Args:
        oncall (list): A list containing the on-call information. The list should have the following elements:
            - uNID (str): The uNID of the on-call person.
            - Name (str): The name of the on-call person.
            - Email (str): The email address of the on-call person.
            - Phone (str): The phone number of the on-call person.

    Returns:
        Table: A `Table` object containing the on-call information.

    """
    table = Table(title="[bold red]On-Call Information", style="red", show_lines=False)
    table.add_column("uNID", style="yellow")
    table.add_column("Name", style="cyan")
    table.add_column("Email", style="magenta")
    table.add_column("Phone", style="green")

    table.add_row(oncall[0], oncall[1], oncall[2], oncall[3])
    
    return table

def main() -> None:
    """
    Main function that performs the on-call information retrieval.

    This function creates a session, logs in using Duo authentication,
    and retrieves the on-call information from the specified URL.

    Raises:
        requests.exceptions.HTTPError: If an HTTP error occurs during the request.

    Returns:
        None
    """
    console = Console()

    # Creating a session and logging in
    duo = Duo(uNID=uNID, password=password)
    s: requests.Session = duo.login()
    requests.urllib3.disable_warnings()
    s.verify = False
    s.get("https://toast.utah.edu/login_helper")
    log.debug("Session created and logged in.")

    response: requests.Response = s.get("https://toast.utah.edu/oncall/oncallinfo")
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        log.error(f"An error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
    
    console.print(table_maker(response.json()["result"]))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
