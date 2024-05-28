#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides a class for performing login to the University of Utah platform with Duo authentication.
"""

# Standard libraries
import logging
from sys import exit
import urllib.parse
from getpass import getpass
from pathlib import Path
import pickle

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
    Represents a Duo authentication handler for the University of Utah platform.

    This class provides methods to perform login with Duo authentication,
    handle Duo two-factor authentication, and store/load session cookies.

    Attributes:
        session (requests.Session): The session object used for making HTTP requests.
        _username (str): The uNID of the user.
        _password (str): The password of the user.
        _prompt_check_times (int): The number of times to check Duo authentication status.
        _login_url (str): The URL for the login page.
        _duo_api_url (str): The URL for the Duo API.
        _test_url (str): The URL for testing authentication.
        cookie_jar (Path): The file path for storing session cookies.

    Methods:
        __init__(self, uNID: str, password: str) -> None:
            Initializes a new instance of the `Duo` class.
        _store_cookies(self) -> None:
            Stores the session cookies in a file.
        _load_cookies(self) -> None:
            Loads the session cookies from a file.
        login(self) -> requests.Session:
            Performs login to the University of Utah platform with Duo authentication.
        handle_duo_auth(self, xsrf: str, auth_url: str) -> None:
            Completes Duo two-factor authentication with user interaction.
    """
    
    def __init__(self, uNID: str, password: str) -> None:
        """
        Initializes a new instance of the `Duo` class.

        Args:
            uNID (str): The uNID of the user.
            password (str): The password of the user.

        Returns:
            None
        """
        self.session = requests.Session()
        self._username = uNID
        self._password = password
        self._prompt_check_times = 3
        self._login_url = "https://go.utah.edu/cas/login"
        self._duo_api_url = "https://api-aba4bf07.duosecurity.com/frame/v4"
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
        try:
            with open(self.cookie_jar, "rb") as file:
                self.session.cookies.update(pickle.load(file))
        except FileNotFoundError:
            # If the file is not found, do nothing
            log.debug("Cookies file not found.")
            pass
        except EOFError:
            # If the file is empty, do nothing
            log.debug("Cookies file is empty.")
            pass

    def _test_authentication(self) -> bool:
        """
        Tests the current session authentication status.
        """
        response: requests.Response = self.session.get(self._login_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        if soup.find("a", attrs={"href": "logout"}):
            return True
        else:
            return False


    def login(self) -> requests.Session:
        """
        Performs login to the University of Utah platform with Duo authentication.

        This method handles the entire login process, including:
            - Obtaining initial execution value from the login page.
            - Performing login with username, password, and execution value.
            - Extracting xsrf and auth_url from the response.
            - Completing Duo authentication with user interaction (push notification, etc.).
            - Returning the session object with final authentication cookies.

        Raises:
            requests.exceptions.RequestException: If any network request fails.
            KeyError: If essential HTML form arguments are not found.
            ValueError: If query parameters are not found in parsed URLs.
        """

        # Load cookies from file if available
        log.debug("Loading cookies from file...")
        self._load_cookies()

        # Test authentication
        log.debug("Testing authentication...")

        if self._test_authentication():
            log.debug("Authentication successful.")
            return self.session
        else:
            log.debug("Authentication failed. Starting login process...")

        # Step 1: Get execution value
        log.debug("Getting execution value...")
        response:requests.Response = self.session.get(self._login_url)
        response.raise_for_status()

        execution_value = get_form_args(response.text, "execution")

        # Step 2: Login with credentials and execution value
        log.debug("Logging in...")
        login_data = {
            "username": self._username,
            "password": self._password,
            "execution": execution_value,
            "_eventId": "submit",
        }
        response = self.session.post(self._login_url, data=login_data, allow_redirects=True)
        response.raise_for_status()

        # Extract xsrf and auth_url from the response
        log.debug("Extracting xsrf and auth_url...")
        xsrf = get_form_args(response.text, "_xsrf")
        auth_url = response.url

        # Step 3: Get important cookies
        log.debug("Getting important cookies...")
        response: requests.Response = self.session.post(auth_url, data={"_xsrf": xsrf})
        response.raise_for_status()

        # Step 4: Handle Duo authentication (separate function)
        log.debug("Handling Duo authentication...")
        self.handle_duo_auth(xsrf, auth_url)

        # Store cookies in a file for future use
        log.debug("Storing cookies in file...")
        self._store_cookies()

        # Login successful! Return the session with cookies
        log.debug("Login successful, returning session.")
        return self.session

    def handle_duo_auth(self, xsrf: str, auth_url: str) -> None:
        """
        Completes Duo two-factor authentication with user interaction.

        This method interacts with the Duo API to initiate and confirm Duo
        authentication based on the user's chosen method (push notification, etc.).

        Args:
            xsrf (str): The xsrf value extracted from the login response.
            auth_url (str): The URL obtained after initial login processing.

        Raises:
            requests.exceptions.RequestException: If any network request fails.
            KeyError: If essential HTML form arguments are not found.
            ValueError: If query parameters are not found in parsed URLs.
        """

        # Step 5: Get sid from auth_url
        log.debug("Getting sid from auth_url...")
        sid = extract_query_parameter(auth_url, "sid")

        # Step 6: Get Duo devices for authentication
        log.debug("Getting Duo devices for authentication...")
        duo_data = {
            "post_auth_action": "OIDC_EXIT",
            "sid": sid,
        }
        response = self.session.get(
            self._duo_api_url + "/auth/prompt/data", params=duo_data
        )
        response.raise_for_status()

        devices = response.json()["response"]["phones"]
        device = devices[0]  # Use the first device for simplicity
        # Maybe add a device selection prompt in the future and a way to store the preferred device
        log.debug(f"Using device: {device['name']}")

        # Step 7: Initiate Duo authentication (push notification, etc.)
        log.debug("Initiating Duo authentication...")
        push_data = {
            "device": device["index"],
            "sid": sid,
            "factor": "Duo Push",
        }
        response = self.session.post(self._duo_api_url + "/prompt", data=push_data)
        response.raise_for_status()

        txid = response.json()["response"]["txid"]
        log.debug(f"Duo authentication initiated, transaction ID: {txid}")

        # Step 8 & 9: Check Duo authentication status
        log.debug("Checking Duo authentication status...")
        for _ in range(self._prompt_check_times):
            status_data = {"txid": txid, "sid": sid}
            response = self.session.post(
                f"{self._duo_api_url}/status", data=status_data
            )
            response.raise_for_status()

            status = response.json()["response"]["status_code"]
            if status == "allow":
                # User accepted the push
                log.debug("Authentication Push accepted.")
                break

            if status == "deny":
                # User denied the push
                log.error("Authentication Push denied.")
                raise LoginError("Authentication Push denied.")

            if status == "timeout":
                # Push timed out
                log.error("Authentication Push timed out.")
                raise LoginError("Authentication Push timed out.")

            log.debug(f"Push status: {status}")
        else:  # If the loop completes without breaking
            raise LoginError(
                f"Duo authentication failed, checked status {self._prompt_check_times} time(s)."
            )

        # Step 10: Finalize Duo authentication with selected device
        log.debug("Finalizing Duo authentication...")
        final_data = {
            "sid": sid,
            "txid": txid,
            "device_key": device["key"],
            "_xsrf": xsrf,
            "dampon_choice": "true",
        }
        response = self.session.post(self._duo_api_url + "/oidc/exit", data=final_data)
        response.raise_for_status()

        # Authentication


def extract_query_parameter(url: str, query_parameter: str) -> str:
    """
    Retrieves the query parameter from the given URL.

    Args:
        url (str): The URL to parse query args from.
        query_parameter (str): The name of the query parameter to retrieve.

    Returns:
        str: The value of the query_parameter extracted from the URL.

    Raises:
        ValueError: If the query_parameter value is not found in the URL.
    """
    param_value = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get(
        query_parameter, [None]
    )[0]
    if param_value is None:
        raise ValueError(f"{query_parameter} not found in the URL {url}")
    return param_value


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
        return BeautifulSoup(html_doc, "html.parser").find(attrs={"name": name})["value"]
    except (TypeError, KeyError):
        raise KeyError(f"{name} not found")


def main() -> None:
    """
    Main function for the UIT Duo authentication tool.
    
    This function handles the authentication process using the Duo authentication system.
    It prompts the user for their uNID and password, and then creates a Duo object to perform the authentication.
    If the `auth` module is available, it uses the pre-configured uNID and password from the `UofU` class.
    Otherwise, it prompts the user to enter their uNID and password manually.
    """

    # Get username and password
    try:
        from auth import UofU
        uNID = UofU.unid
        password = UofU.cisPassword
    except ImportError:
        uNID = input("Enter your uNID: ")
        password = getpass("Enter your: cis password: ")

    import argparse
    parser = argparse.ArgumentParser(description="University of Utah Duo Authentication")
    parser.add_argument("-d", "--debug", help="Enable debug logging", action="store_true")
    args = parser.parse_args()

    if args.debug:
        log.setLevel(logging.DEBUG)

    # Create Duo object and login
    duo = Duo(uNID, password)
    duo.login()
    print("Login successful! And cookies should be updated in the file.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
