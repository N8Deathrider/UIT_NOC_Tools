#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#TODO: Add description
"""

# Standard libraries
import logging
from sys import exit

# Third-party libraries
from rich.logging import RichHandler
from rich.table import Table
from rich.panel import Panel
import requests
from rich import print, inspect  # DEBUG
from yarl import URL

# Local libraries


# Standard exit codes
EXIT_SUCCESS = 0  # No errors
EXIT_GENERAL_ERROR = 1  # General error
EXIT_INVALID_ARGUMENT = 120  # Invalid argument to exit
EXIT_KEYBOARD_INTERRUPT = 130  # Keyboard interrupt (Ctrl+C)

# Constants
BASE_URL = URL("https://people.utah.edu/")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)
log: logging.Logger = logging.getLogger("rich")


def get_args():
    ...


def basic_search(search_term: str) -> list[dict[str, str]]:
    """
    #TODO Add description
    """
    basic_search_data = {
        "searchTerm": search_term,
    }
    response: requests.Response = requests.post(
        url=BASE_URL / "uWho/basic.hml",
        data=basic_search_data,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    response.raise_for_status()
    return response.text


def main() -> None:
    """
    #TODO: Add description
    """
    search_results = basic_search("u1377551")
    print(search_results)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
