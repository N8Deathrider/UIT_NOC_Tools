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
from bs4 import BeautifulSoup

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


def get_form_args(html_doc: str, name) -> str:
    """
    Retrieves the value of an HTML attribute with the specified name from the given HTML document.

    Args:
        html_doc (str): The HTML document as a string.
        name: The name of the attribute to retrieve.

    Returns:
        str: The value of the attribute.

    Raises:
        KeyError: If the attribute with the specified name is not found.
    """
    try:
        return BeautifulSoup(html_doc, "html.parser").find(attrs={"name": name})[
            "value"
        ]
    except (TypeError, KeyError):
        raise KeyError(f"{name} not found")


def basic_search(search_term: str) -> list[dict[str, str]]:
    """
    #TODO Add description
    """
    # Create a session
    session: requests.Session = requests.Session()

    # Get the search page for cookies and CSRF token
    response: requests.Response = session.get(BASE_URL / "uWho/basic.hml")
    response.raise_for_status()

    # Perform the search
    search_data = {
        "searchTerm": search_term,
        "_csrf": get_form_args(response.text, "_csrf"),
    }
    response: requests.Response = session.post(
        url=BASE_URL / "uWho/basic.hml", data=search_data
    )
    response.raise_for_status()

    # Parse the search results
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
