#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#TODO: Add description
"""
# Look at https://noc-dnac.net.utah.edu/dna/platform/app/consumer-portal/developer-toolkit/apis
# for more information on the API.

# TODO: make a better name for this script

# Standard libraries
import logging
import argparse
from netaddr.eui import EUI
from netaddr import mac_unix_expanded
from sys import exit

# Third-party libraries
import requests
from pyperclip import copy, paste
from rich import print as rprint
from rich.logging import RichHandler
from rich_argparse import RichHelpFormatter
from yarl import URL

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


def get_credentials() -> tuple[str, str]:
    try:
        from auth import UofU
        unid = UofU.unid
        wian_password = UofU.pciPassword
    except ImportError:
        log.error("The 'auth.py' not found.")
        from getpass import getpass
        unid = input("Enter your uNID: ")
        wian_password = getpass("Enter your WIAN password: ")

    return unid, wian_password


def get_args() -> argparse.Namespace:
    """
    """
    parser = argparse.ArgumentParser(
        description="",
        formatter_class=RichHelpFormatter
    )

    parser.add_argument(
        "mac_address",
        type=str,
        help="The MAC address of the device you want to look up.",
        default=paste(),
        nargs="?"
    )

    return parser.parse_args()


def main() -> None:
    """
    #TODO: Add description
    """
    base_url = URL("https://noc-dnac.net.utah.edu/dna/")
    system_base_url = base_url / "system/api/v1/"
    intent_base_url = base_url / "intent/api/v1/"

    session = requests.Session()
    session.verify = False
    requests.packages.urllib3.disable_warnings()

    token = session.post(system_base_url / "auth/token", auth=get_credentials()).json()["Token"]

    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }

    session.headers.update(headers)

    response = session.get(
        intent_base_url / "client-detail", params={"macAddress": "d4:57:63:d8:2c:3a"}
    )
    response.raise_for_status()
    client_details = response.json()

    response = session.get(
        intent_base_url / "user-enrichment", headers={"entity_type": "mac_address", "entity_value": "d4:57:63:d8:2c:3a"}
    )
    response.raise_for_status()
    user_enrichment = response.json()

    rprint(client_details)


def main2() -> None:
    """
    """
    ARGS = get_args()

    mac_address = str(EUI(ARGS.mac_address, dialect=mac_unix_expanded))

    base_url = URL("https://noc-dnac.net.utah.edu/dna/")
    system_base_url = base_url / "system/api/v1/"
    intent_base_url = base_url / "intent/api/v1/"

    session = requests.Session()
    session.verify = False
    requests.packages.urllib3.disable_warnings()

    token = session.post(system_base_url / "auth/token", auth=get_credentials()).json()[
        "Token"
    ]

    headers = {"X-Auth-Token": token, "Content-Type": "application/json"}

    session.headers.update(headers)

    response = session.get(
        intent_base_url / "client-detail", params={"macAddress": mac_address}
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if not response.json()['detail']:
            log.error("Client not found.")
            exit(EXIT_GENERAL_ERROR)
        else:
            log.error(f"An error occurred: {e}")
            exit(EXIT_GENERAL_ERROR)

    try:
        client_details = (
            f"MAC Address: {response.json()['detail']['hostMac']}\n"
            f"IP Address: {response.json()['detail']['hostIpV4']}\n"
            f"Location: {response.json()['detail']['location']}\n"
            f"SSID: {response.json()['detail']['ssid']}\n"
            f"AP Name: {response.json()['detail']['connectedDevice'][0]['name']}"
        )
    except KeyError as e:
        rprint(response.json())
        exit(EXIT_GENERAL_ERROR)

    rprint(client_details)
    copy(client_details)


if __name__ == "__main__":
    try:
        main2()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
