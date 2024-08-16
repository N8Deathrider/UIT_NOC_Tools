#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#TODO: Add description
"""

# Standard libraries
import logging
from sys import exit

# Third-party libraries
import requests
from rich.logging import RichHandler
from yarl import URL

# Local libraries
from uit_duo import Duo


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


class SNow:
    def __init__(self, username: str, password: str) -> None:
        self._duo = Duo(username, password)
        self.base_url = URL("https://uofu.service-now.com/")

    def auth(self) -> None:
        self._session: requests.Session = self._duo.login()
