#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#TODO: Add description
"""

# Standard libraries
import argparse
import logging
from io import StringIO
from sys import exit

# Third-party libraries
import pandas as pd
import requests
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


def get_args() -> argparse.Namespace:
    """
    Parse command line arguments and return the parsed arguments.

    Returns:
        argparse.Namespace: The parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="A script to lookup building information at UIT"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help=argparse.SUPPRESS
    )

    parser.add_argument(
        "building_number",
        type=int,
        help="The building number to lookup"
        # TODO: look at adding more arguments so that multiple buildings can be looked up at once
    )

    return parser.parse_args()


def get_table_data() -> pd.DataFrame:
    """
    Fetches table data from a URL and returns it as a pandas DataFrame.

    Returns:
        pd.DataFrame: The table data as a pandas DataFrame.
    """
    URL = "https://www.space.utah.edu/htdocs/requestBuildingList.php"
    post_data = {
        "tried": "yes",
        "form_change": "no",
        "fetch_button": "Fetch+List",
        "delivery": "online",
        "status": "active"
    }
    response = requests.post(url=URL, data=post_data)
    dfs = pd.read_html(StringIO(response.text))
    df = dfs[1]
    df.set_index("Building Number", inplace=True, drop=False)
    return df


def main() -> None:
    """
    #TODO: Add description
    """
    ARGS = get_args()

    if ARGS.debug:
        log.setLevel(logging.DEBUG)

    log.debug(f"ARGS: {ARGS}")

    table_data = get_table_data()
    log.debug(f"Table data (First 5 rows): {table_data.head()}")

    selected_row = table_data.loc[ARGS.building_number]
    print(selected_row)


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
