#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#TODO: Add description
"""

# Standard libraries
import logging
from sys import exit
import urllib.parse
from getpass import getpass
from pathlib import Path
import pickle
import urllib3

# Third-party libraries
from rich.logging import RichHandler
from bs4 import BeautifulSoup
import requests

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


class LoginError(Exception):
    pass


class Duo:
    """
    #TODO: Add description
    """

    def __init__(self, uNID: str, password: str) -> None:
        """
        #TODO: Add description
        """
        self.session = requests.Session()
        self._username = uNID
        self._password = password
        self._login_url = "https://go.utah.edu/cas/login"
        self._api_url = "https://api-aba4bf07.duosecurity.com/frame/v4"
        self._test_url = "https://portal.app.utah.edu/api-proxy/cis-api/user/current"
        self.cookie_jar = Path.home().joinpath(".uit_duo_cookies")

        self.session.headers.update(
            {"User-Agent": f"{uNID}-python-requests", "UNID": uNID}
        )

    def _store_cookies(self) -> None:
        """
        Stores the session cookies in a file.

        This method serializes the session cookies and saves them to a file using pickle.
        The file path is specified by the `cookie_jar` attribute of the class.
        """
        with open(self.cookie_jar, "wb") as file:
            pickle.dump(self.session.cookies, file)

    def _load_cookies(self) -> None:
        """
        Loads the session cookies from a file.

        This method loads the session cookies from a file using pickle.
        The file path is specified by the `cookie_jar` attribute of the class.
        """
        with open(self.cookie_jar, "rb") as file:
            self.session.cookies.update(pickle.load(file))

    def _get_execution_value(self) -> str:
        """
        Retrieves the execution value from the login page.

        Returns:
            str: The execution value.
        """
        response: requests.Response = self.session.get(url=self._login_url)
        response.raise_for_status()  # Raise an exception if the response is not 200
        return get_form_args(response.text, "execution")

    def _get_xsrf(self, execution: str) -> tuple[str, str]:
        """
        Get the XSRF token and the response URL after logging in.

        Args:
            execution (str): The execution value for authentication.

        Returns:
            tuple[str, str]: A tuple containing the XSRF token and the response URL.
        """
        response: requests.Response = self.session.post(
            url=self._login_url,
            data={
                "username": self._username,
                "password": self._password,
                "_eventId": "submit",
                "execution": execution,
            }
        )
        response.raise_for_status()  # Raise an exception if the response is not 200

        return get_form_args(response.text, "_xsrf"), response.url

    def auth_test(self) -> bool:
        """
        Performs an authentication test by sending a GET request to the test URL.

        Returns:
            bool: True if the response is successful (status code 200), False otherwise.
        """
        response: requests.Response = self.session.get(self._test_url)
        return response.ok

    def authenticate(self) -> requests.Session:
        """
        Authenticates the user and returns a session object.

        This method loads the cookies, checks if the authentication is successful,
        and if not, it attempts to log in. If the authentication still fails,
        an error is logged and a LoginError is raised.

        Returns:
            requests.Session: The authenticated session object.

        Raises:
            LoginError: If the authentication fails.
        """
        self._load_cookies()
        if not self.auth_test():
            self.login()
            if not self.auth_test():
                log.error("Authentication failed. Please check your credentials and try again.")
                raise LoginError("Authentication failed. Please check your credentials and try again.")

            self._store_cookies()

        return self.session


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


def main() -> None:
    """
    #TODO: Add description
    """
    ...


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
