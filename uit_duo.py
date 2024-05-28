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


class Device:
    """
    Represents a device used for authentication in Duo Security.

    Attributes:
        key (str): The unique identifier of the device.
        name (str): The name of the device.
        sms_batch_size (int): The batch size for sending SMS messages.
        index (str): The index of the device.
        requires_compliance_text (bool): Indicates if the device requires compliance text.
        keypress_confirm (str): The keypress confirmation for the device.
        end_of_number (str): The end of the phone number for the device.
        mobile_otpable (bool): Indicates if the device supports mobile OTP.

    Methods:
        push(sid: str) -> str:
            Sends a Duo Push authentication request to the device.

        get_status(txid: str) -> str:
            Retrieves the status of a Duo Push authentication request.

    """

    def __init__(self, phone: dict, session: requests.Session, api_url: str) -> None:
        self._session = session
        self._api_url = api_url
        self.key: str | None = phone.get("key")
        self.name: str | None = phone.get("name")
        self.sms_batch_size: int | None = phone.get("sms_batch_size")
        self.index: str | None = phone.get("index")
        self.requires_compliance_text: bool | None = phone.get(
            "requires_compliance_text"
        )
        self.keypress_confirm: str | None = phone.get("keypress_confirm")
        self.end_of_number: str | None = phone.get("end_of_number")
        self.mobile_otpable: bool | None = phone.get("mobile_otpable")

    def push(self, sid: str) -> str:
        """
        Sends a Duo Push authentication request to the device.

        Args:
            sid (str): The session ID for the authentication request.

        Returns:
            str: The transaction ID (txid) of the authentication request.

        Raises:
            ValueError: If the transaction ID (txid) is not found in the response.

        """
        self.sid = sid
        response: requests.Response = self._session.post(
            url=f"{self._api_url}/prompt",
            data={"device": self.index, "factor": "Duo Push", "sid": self.sid},
        )
        response.raise_for_status()
        try:
            txid = response.json()["response"]["txid"]
        except KeyError:
            raise ValueError("txid not found")
        return txid

    def get_status(self, txid: str) -> str:
        """
        Retrieves the status of a Duo Push authentication request.

        Args:
            txid (str): The transaction ID (txid) of the authentication request.

        Returns:
            str: The status code of the authentication request.

        """
        response: requests.Response = self._session.post(
            f"{self._api_url}/status", data={"txid": txid, "sid": self.sid}
        )
        response.raise_for_status()
        return response.json()["response"]["status_code"]


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
        self._duo_api_url = "https://api-aba4bf07.duosecurity.com/frame/v4"
        self._test_url = "https://portal.app.utah.edu/api-proxy/password-change-api/status/01377551"
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
        response: requests.Response = self.session.get(self._test_url)
        response.raise_for_status()

        if response.ok:
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
            xsrf: The xsrf value extracted from the login response.
            auth_url: The URL obtained after initial login processing.

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

        log.debug(f"Duo authentication initiated, transaction ID: {txid}")
        txid = response.json()["response"]["txid"]

        # Step 8 & 9: Check Duo authentication status (loop 3 times)
        log.debug("Checking Duo authentication status...")
        for _ in range(3):
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
            log.debug(f"Push status: {status}")
        else:  # If the loop completes without breaking
            raise LoginError("Duo authentication failed, checked status 3 times.")

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
        return BeautifulSoup(html_doc, "html.parser").find(attrs={"name": name})[
            "value"
        ]
    except (TypeError, KeyError):
        raise KeyError(f"{name} not found")


def check_status(device: Device, txid: str, times: int = 3):
    """
    Check the status of a push notification on the device.

    Args:
        device (Device): The device object representing the user's device.
        txid (str): The transaction ID of the push notification.
        times (int): The number of times to check the status.

    Returns:
        None

    Raises:
        LoginError: If the user denies the push notification, if the push notification times out,
                    or if an unexpected status is received after checking the status multiple times.
    """
    for _ in range(times):
        status = device.get_status(txid)  # Get the status of the push
        if status == "allow":
            # User accepted the push
            log.debug("Authentication Push accepted.")
            break
        elif status == "pushed":
            # Push was sent
            log.debug("Push was sent.")
            pass
        elif status == "deny":
            # User denied the push
            log.error("Authentication Push denied.")
            raise LoginError("Authentication Push denied.")
        elif status == "timeout":
            # Push timed out
            log.error("Authentication Push timed out.")
            raise LoginError("Authentication Push timed out.")
        else:
            # Unexpected status
            log.error(f"Got an unexpected status: {status}")
            raise LoginError(f"Got an unexpected status: {status}")
    else:
        log.error(f"Authentication Push status check failed. Checked {times} times.")
        raise LoginError(f"Authentication Push status check failed. Checked {times} times.")


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
