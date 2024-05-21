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


class Duo:
    """
    #TODO: Add description
    """

    def __init__(self, uNID: str, password: str) -> None:
        """
        #TODO: Add description
        """
        self.session = requests.Session()
        self._login_url = "https://go.utah.edu/cas/login"
        self._api_url = "https://api-aba4bf07.duosecurity.com/frame/v4"
        self._test_url = "https://portal.app.utah.edu/api-proxy/cis-api/user/current"
        self.cookie_jar = Path.home().joinpath(".uit_duo_cookies")

        self.session.headers.update(
            {"User-Agent": f"{uNID}-python-requests", "UNID": uNID}
        )

    def store_cookies(self) -> None:
        """
        Stores the session cookies in a file.

        This method serializes the session cookies and saves them to a file using pickle.
        The file path is specified by the `cookie_jar` attribute of the class.
        """
        with open(self.cookie_jar, "wb") as file:
            pickle.dump(self.session.cookies, file)

    def load_cookies(self) -> None:
        """
        Loads the session cookies from a file.

        This method loads the session cookies from a file using pickle.
        The file path is specified by the `cookie_jar` attribute of the class.
        """
        with open(self.cookie_jar, "rb") as file:
            self.session.cookies.update(pickle.load(file))

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
            Authenticates the user and returns a requests.Session object.

            This method first tries to load the stored cookies. If the cookies are not found or expired,
            it checks if the authentication is successful by calling the `auth_test` method. If the authentication
            fails, it prompts the user to login and stores the cookies for future use.

            Returns:
                A requests.Session object that can be used for making authenticated requests.

            """
            self.load_cookies()
            if not self.auth_test():
                self.login()
                self.store_cookies()
            return self.session


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
