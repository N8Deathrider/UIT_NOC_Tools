#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#TODO: Add description
"""

# Standard libraries
import argparse
import logging
from sys import exit

# Third-party libraries
import requests
from rich.logging import RichHandler

# Local libraries
from uit_duo import Duo

try:
    from auth import UofU

    uNID = UofU.unid
    password = UofU.cisPassword
except ImportError:
    from getpass import getpass

    uNID = input("Enter your uNID: ")
    password = getpass("Enter your: cis password: ")

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
    """
    raise NotImplementedError


def main() -> None:
    """
    #TODO: Add description
    """
    ARGS = get_args()
    log.debug(f"Arguments: {ARGS}")

    # Create Duo object
    duo = Duo(uNID, password)
    log.debug("Duo object created.")
    
    # Create session
    s: requests.Session = duo.login()
    log.debug("Session created.")
    
    # Nessisary actions for TOAST login
    requests.urllib3.disable_warnings()
    s.verify = False
    s.get("https://toast.utah.edu/login_helper")
    log.debug("Nessisary actions for TOAST login completed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
