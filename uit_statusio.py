#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A simple script to retrieve the status information from the status.io API and display it in the terminal.
"""

# Standard libraries
import logging
from sys import exit

# Third-party libraries
import requests
from rich.logging import RichHandler
from rich import print as rprint
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

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


class TermColors:
    # Foreground colors
    RESET_ALL = '\033[0m'
    BLACK = '\033[30m'
    RED = '\033[31m'
    ORANGE = '\033[38;5;202m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    DEFAULT = '\033[39m'


def main1():
    """
    #TODO: Add docstring
    """
    url = 'https://api.status.io/1.0/status/561446c409989c1d2d000e99'
    final_text = []
    status_colors = {
        100: TermColors.GREEN,
        200: TermColors.YELLOW,
        300: TermColors.RED,
        400: TermColors.ORANGE,
        500: TermColors.CYAN,
        600: TermColors.MAGENTA,
        0: TermColors.RESET_ALL
    }
    r = requests.get(url=url)
    if r.ok:
        pass
    else:
        exit(f'{r.status = } {r.text = } {r.reason = }')

    status_json = r.json()['result']
    overall_status = status_json['status_overall']
    status_list = status_json['status']

    final_text.append(f'Overall status: {status_colors[overall_status["status_code"]]}{overall_status["status"]}{status_colors[0]}')

    for status_item in status_list:
        final_text.append(f'● {status_item["name"] + ":":.<33}{status_colors[status_item["status_code"]]}{status_item["status"]}{status_colors[0]}')

    print('\n'.join(final_text))


def get_status():
    """
    Retrieves the status information from the status.io API.

    Returns:
        dict: The status information as a dictionary.
    """
    url = "https://api.status.io/1.0/status/561446c409989c1d2d000e99"
    r: requests.models.Response = requests.get(url=url)
    r.raise_for_status()
    return r.json()["result"]


def get_status_color(status: dict[str, str]) -> str:
    """
    Returns the color associated with a given status.

    Args:
        status (dict[str, str]): The status dictionary containing the "status" key.

    Returns:
        str: The color associated with the status. If the status is not found in the dictionary,
             the default color "red" is returned.
    """
    status_colors: dict[str, str] = {  # https://blog.status.io/2014/03/07/custom-status-levels/
        "Operational": "#27AE60",
        "Degraded Performance": "#FFA837",
        "Partial Service Disruption": "#FFA837",
        "Full Service Disruption": "#C44031",
        "Security Breach": "#C44031",
        "Planned Maintenance": "#00AAF0"
    }
    return status_colors.get(status["status"], "red")


def main2():
    """
    #TODO: Add docstring
    """
    status_info = get_status()

    overall_status = status_info["status_overall"]
    status_list = status_info["status"]

    table = Table(
        title=f"[b]Overall status[/b]: [{get_status_color(overall_status)}]{overall_status['status']}",
        show_header=False,
        style="red"
    )

    for status_item in status_list:
        name = status_item["name"]
        status = status_item["status"]
        table.add_row(f"[b]{name}[/b]", f"[{get_status_color(status_item)}]{status}")

    rprint(table)


def main3():
    """
    #TODO: Add docstring
    """
    status_info = get_status()

    overall_status = status_info["status_overall"]
    status_list = status_info["status"]

    status_panels = []

    for status_item in status_list:
        name = status_item["name"]
        status = status_item["status"]
        status_panels.append(Panel(f"[b]{name}[/b]\n[{get_status_color(status_item)}]{status}", expand=True))

    rprint(Columns(status_panels))



if __name__ == "__main__":
    try:
        # main1()
        main2()
        # main3()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
