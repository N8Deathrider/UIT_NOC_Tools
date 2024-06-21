#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script retrieves the uptime of a switch or switches and displays the information.

The script uses command line arguments to specify the switch address(es) and an optional debug flag.
It imports the Switch class from the SwitchInfo module to interact with the switches.
The uptime information is retrieved from the switch and displayed using the rich library for formatting.

Usage:
    python uit_uptime.py [-d] switch [switch ...]

Arguments:
    switch: The switch address(es) to retrieve uptime information for.

Exit Codes:
    0: No errors.
    1: General error.
    120: Invalid argument to exit.
    130: Keyboard interrupt (Ctrl+C).
"""

# Standard libraries
import logging
from sys import exit
import argparse

# Third-party libraries
from rich.logging import RichHandler
from rich import print as rprint
from rich.table import Table
from rich.console import Console

# Local libraries
from SwitchInfo import Switch

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
logging.getLogger("paramiko").setLevel(logging.WARNING)


def get_args() -> argparse.Namespace:
    """
    Get command line arguments for getting the uptime of a switch or switches.

    Returns:
        argparse.Namespace: The parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description="Get the uptime of a switch or switches.")

    parser.add_argument("-d", "--debug", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("switch", type=str, help="The switch address.", nargs="+")

    return parser.parse_args()


def table_gen(switches: list) -> Table:
    """
    Generate a table with the uptime information for the specified switches.

    Args:
        switches (list): The list of switches to get uptime information for.

    Returns:
        Table: The table with the uptime information.
    """
    console = Console()
    table = Table(title="Switch Uptime Information")
    table.add_column("Switch", style="cyan", no_wrap=False)
    table.add_column("Uptime", style="magenta", no_wrap=True)
    table.add_column("Days up", style="yellow", no_wrap=True)
    table.add_column("Restart timestamp", style="green", no_wrap=True)
    table.add_column("Reason", style="bright_blue", no_wrap=True)

    with console.status("[green]Retrieving uptime information...") as status:
        for switch in switches:
            status.update(f"[green]Retrieving uptime information for [cyan]{switch}[/cyan]...")
            switch_obj = Switch(switch)
            uptime = switch_obj.uptime[3]
            restart_timestamp = switch_obj.uptime[1].format("ddd, MMM D YYYY [a]t, h:mm A")
            days_up = str(switch_obj.uptime[0])
            row = (switch, uptime.get("uptime"), days_up, restart_timestamp , uptime.get("reload_reason"))
            log.debug(f"Row: {row}")
            table.add_row(*row)

    return table


def main() -> None:
    """
    This is the main function that performs the main logic of the program.

    It retrieves command line arguments, sets up the message template, and iterates over the specified switches to calculate and display their uptime.

    Args:
        None

    Returns:
        None
    """
    ARGS = get_args()

    if ARGS.debug:
        log.setLevel(logging.DEBUG)

    log.debug(f"Arguments: {ARGS}")

    table = table_gen(ARGS.switch)
    rprint(table)

if __name__ == "__main__":
    try:
        main()
        exit(EXIT_SUCCESS)
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
