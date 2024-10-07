#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script is used to lookup building information at UIT.

It fetches table data from a URL, converts it to a pandas DataFrame, and displays the information in a rich table.

Usage:
    python uit_building_lookup.py [options] building_number(s)

Options:
    --debug     Enable debug mode
    building_number(s)   The building number(s) to lookup

Example:
    python uit_building_lookup.py --debug 12345 67890
"""

# Standard libraries
import argparse
import logging
from io import StringIO
from sys import exit

# Third-party libraries
import pandas as pd
import requests
from rich_argparse import RichHelpFormatter
from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler

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

# TODO: Add argument for All buildings, Active buildings, or Inactive buildings with choices and Active as default
def get_args() -> argparse.Namespace:
    """
    Parse command line arguments and return the parsed arguments.

    Returns:
        argparse.Namespace: The parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="A script to lookup building information at UIT",
        formatter_class=RichHelpFormatter,
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help=argparse.SUPPRESS
    )

    parser.add_argument(
        "-s",
        "--status",
        default="active",
        help="The status of the building(s) to lookup. Default is 'active'.",
        choices=["active", "inactive", "all"],
        type=str
    )

    parser.add_argument(
        "building_number",
        type=int,
        help="The building number to lookup",
        nargs="+"
    )

    return parser.parse_args()


def get_table_data(status: str = "active") -> pd.DataFrame:
    """
    Fetches table data from a URL and returns it as a pandas DataFrame.

    Returns:
        pd.DataFrame: The table data as a pandas DataFrame.
    """
    URL = "https://www.space.utah.edu/htdocs/requestBuildingList.php"
    if status not in ["active", "inactive", "all"]:
        raise ValueError("Invalid status. Must be one of 'active', 'inactive', or 'all'.")
    post_data = {
        "tried": "yes",
        "form_change": "no",
        "fetch_button": "Fetch+List",
        "delivery": "online",
        "status": status
    }
    response = requests.post(url=URL, data=post_data)
    dfs = pd.read_html(StringIO(response.text))
    df = dfs[1].fillna("")
    df.set_index("Building Number", inplace=True, drop=False)
    return df


def build_rich_table(df: pd.DataFrame, building_numbers: list[int]) -> Table:
    """
    Converts a pandas DataFrame to a rich Table.

    Args:
        df (pd.DataFrame): The pandas DataFrame to convert.
        building_numbers (list[int]): The building numbers to include in the rich Table.

    Returns:
        Table: The rich Table.
    """
    table = Table(
        title="Building Information",
        show_header=True,
        style="red",
        header_style="bold",
        show_lines=True,
    )

    df = df.drop(["NASF", "NSF", "GSF", "Location Code"], axis=1, inplace=False)

    for column in df.columns:
        table.add_column(column)
    for row in df.itertuples(index=False):
        if row[0] in building_numbers:
            row = map(str, list(row))
            table.add_row(*row)
    return table


def main() -> None:
    """
    Entry point of the program.
    
    This function retrieves command line arguments, sets the logging level based on the debug flag,
    retrieves table data, and prints a rich table based on the provided building number.
    """
    ARGS = get_args()

    if ARGS.debug:
        log.setLevel(logging.DEBUG)

    log.debug(f"ARGS: {ARGS}")

    table_data = get_table_data(status=ARGS.status)
    log.debug(f"Table data (First 5 rows): {table_data.head()}")

    console.print(build_rich_table(table_data, ARGS.building_number))


if __name__ == "__main__":
    try:
        console = Console()
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
