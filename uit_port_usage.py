#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#TODO: Add description
"""

# Standard libraries
import argparse
import json
import logging
from sys import exit
from time import sleep

# Third-party libraries
import requests
from rich_argparse import RichHelpFormatter
from rich.logging import RichHandler
from rich.table import Table
from rich import print as rprint
from yarl import URL

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

BASE_URL = URL("https://toast.utah.edu/reports")


def get_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="This script will check when the last packet was sent or received on each port on a specified switch using a report run by TOAST. It will return a list of ports that have not had any traffic within a specified amount of time (default of 90 days).",
        formatter_class=RichHelpFormatter,
    )

    parser.add_argument("--debug", action="store_true", help=argparse.SUPPRESS)

    parser.add_argument(
        "-d",
        "--days",
        type=int,
        metavar="days",
        help="Maximum Amount of Idle Days"
    )

    parser.add_argument(
        "switch",
        type=str,
        metavar="switch_name_or_ip",
        help="The switch to retrieve port usage data from."
    )

    return parser.parse_args()


def start_report(session: requests.Session, switch: str, days: int | None = None) -> int:
    """
    Start the report for the specified switch.

    Args:
        session (requests.Session): Session object.
        switch (str): Switch name or IP address.
        days (int): Maximum amount of idle days.

    Returns:
        int: Report ID.
    """
    url = BASE_URL / "report"

    inputs = {
        "input_switchnameorip": switch,
        "input_maximumamountofidledays": days or ""
    }

    form_data = {
        "type": "report_portusage",
        "inputs": json.dumps(inputs, separators=(",", ":"))
        # The separators argument is used to prevent spaces from being added to the JSON string.
        # This is necessary for the TOAST API validation for some reason.
    }
    log.debug(f"Form data: {form_data}")

    response: requests.Response = session.post(url, data=form_data)
    log.debug(f"Response: {response}")

    response.raise_for_status()
    # TODO: Add error handling

    log.debug(f"Response JSON: {response.json()}")
    return int(response.json()["result"])


def get_report_data(session: requests.Session, report_id: str | int) -> list[list[str]]:
    """
    Retrieves report data from the specified report ID.

    Args:
        session (requests.Session): The session object used to make the HTTP request.
        report_id (str | int): The ID of the report to retrieve.

    Returns:
        list[list[str]]: A list of lists containing the report data, where each inner list represents a row of data.

    Raises:
        requests.HTTPError: If the HTTP request to retrieve the report fails.
    """
    url = BASE_URL / "report"

    if isinstance(report_id, str):
        report_id = int(report_id)

    response: requests.Response = session.get(url, params={"id": report_id})

    response.raise_for_status()
    # TODO: Add error handling

    data = response.json()["data"].splitlines()

    for index, line in enumerate(data):
        data[index] = line.split(",")

    return data


def display_report(data: list[list[str]], switch) -> None:
    """
    Display a port usage report for a given switch.

    Args:
        data (list[list[str]]): The data to be displayed in the report.
        switch: The name of the switch for which the report is generated.

    Returns:
        None
    """
    table = Table(title=f"Port Usage Report for: [bold]{switch}", style="red")

    headers = data.pop(0)

    uptime_header = headers.pop()

    uptime_data = data.pop(0)
    uptime_data.pop(0)  # Remove the first element, which is the same as the header.
    uptime_data.pop(0)  # Remove the new first element, which is an empty string.

    for header in headers:
        table.add_column(header)

    for row in data:
        table.add_row(*row)

    table.caption = f"{uptime_header}: {','.join(uptime_data)}"

    rprint(table)


def main() -> None:
    """
    #TODO: Add description
    """
    ARGS = get_args()

    if ARGS.debug:
        log.setLevel(logging.DEBUG)
        log.debug("Debug mode enabled.")

    log.debug(f"Arguments: {ARGS}")

    # Create Duo object
    duo = Duo(uNID, password)
    log.debug("Duo object created.")

    # Create session
    s: requests.Session = duo.login()
    log.debug("Session created.")

    # Necessary actions for TOAST login
    requests.urllib3.disable_warnings()
    s.verify = False
    s.get("https://toast.utah.edu/login_helper")
    log.debug("Necessary actions for TOAST login completed.")

    # Start report
    report_id = start_report(s, ARGS.switch, ARGS.days)
    log.debug(f"Report ID: {report_id}")

    # Get report data
    sleep(2)
    # Sleep for 2 seconds to allow the report to be generated, the API method to check report status does not work.
    report_data = get_report_data(s, report_id)

    # Display report
    display_report(report_data, ARGS.switch)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
