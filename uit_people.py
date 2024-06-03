#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#TODO: Add description
"""

# Standard libraries
import logging
from sys import exit
import argparse

# Third-party libraries
from rich.logging import RichHandler
from rich.table import Table
from rich.panel import Panel
import requests
from rich import print as rprint
from yarl import URL
from bs4 import BeautifulSoup
import pandas as pd

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


def get_args() -> argparse.Namespace:
    """
    Parse command line arguments for searching the University of Utah people directory.

    Returns:
        argparse.Namespace: The parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description="Search the University of Utah people directory.")
    parser.add_argument("search_term", type=str, help="The term to search for.")
    parser.add_argument(
        "--max-results",
        "-m",
        type=int,
        help="The max number of results to display.",
        default=None,
    )
    return parser.parse_args()


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


def fix_email_string(email: str) -> str:
    """
    Fix the email string by removing any extra characters.

    Args:
        email (str): The email string to fix.

    Returns:
        str: The fixed email string.
    """
    return (
        email.split('" + ">"')[0]
        .replace('<!--  document.write("<a href=" + "mail" + "to:" + "', "")
        .replace('" + "@" + "', "@")
    )


def parse_search_results_page(html_doc: str) -> list[dict[str, str]]:
    """
    Parse the search results page and return the search results as a list of dictionaries.

    Parameters:
    - html_doc (str): The HTML document containing the search results.

    Returns:
    - list[dict[str, str]]: A list of dictionaries representing the search results. Each dictionary contains the following keys:
        - "Name" (str): The name of the person.
        - "Title" (str): The persons job title.
        - "Email" (str): The email address of the person.
        - "Dept/Org" (str): The department or organization the person belongs to.
        - "Phone" (str): The phone number of the person.
    """
    dfs = pd.read_html(html_doc)
    df = dfs[0]
    df[["Name", "Title"]] = df["Name & Title"].str.split("  ", n=1, expand=True)
    df.drop(columns=["Name & Title"], inplace=True)
    df["Title"] = df["Title"].str.strip()
    df["Email"] = df["Email"].apply(fix_email_string)
    return df.to_dict("records")


def display_results_table(results: list[dict[str, str]], max_results: int | None = None) -> None:
    """
    Display the search results in a table.

    Args:
        results (list[dict[str, str]]): The search results to display.
        max_results (int): The max number of results to display.
    """
    table: Table = Table(title="Search Results", row_styles=["none", "dim"])
    table.add_column("Name", style="cyan")
    table.add_column("Title", style="magenta")
    table.add_column("Email", style="green")
    table.add_column("Dept/Org", style="blue")
    table.add_column("Phone", style="yellow")

    if max_results:
        results = results[:max_results]

    for result in results:
        table.add_row(
            result["Name"],
            result["Title"],
            result["Email"],
            result["Dept/Org"],
            result["Phone"],
        )

    rprint(Panel(table, expand=False))


def basic_search(search_term: str) -> list[dict[str, str]]:
    """
    Perform a basic search for a given search term.

    Args:
        search_term (str): The term to search for.

    Returns:
        list[dict[str, str]]: A list of dictionaries representing the search results.
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
    return parse_search_results_page(response.text)


def advanced_search(search_term: str) -> list[dict[str, str]]:
    ...


def main() -> None:
    """
    #TODO: Add description
    """
    args = get_args()

    search_results = basic_search(args.search_term)
    display_results_table(search_results, args.max_results)
    # TODO: add arg for displaying results as a table or some other format
    # TODO: add arg for specifying the number of results to display that defaults to None (all results)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
