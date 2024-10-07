#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script provides functions for routing requests to the appropriate queue and generating a formatted message with routing information and a Teams link.

The script includes the following functions:
- get_args(): Gets the arguments passed to the script.
- message_builder(): Builds a message with routing information and a Teams link.
- queue_search(): Searches for a queue based on a query.
- router_v3(): Routes the request to the appropriate queue based on the provided arguments.
- router_v4(): Routes the request to the appropriate queue based on the provided arguments.

The script also includes standard exit codes and logging setup.

Author: Nathan Cable
"""


# Standard libraries
import argparse
import logging
from sys import exit

# Third-party libraries
from fuzzyset import FuzzySet
import pyperclip as pc
from rich_argparse import RichHelpFormatter
from rich import print as rprint
from rich.logging import RichHandler
from rich.prompt import Prompt

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


def get_args() -> argparse.Namespace:
    """
    This function gets the arguments passed to the script.

    Args:
        None

    Returns:
        args: The arguments passed to the script
    """
    parser = argparse.ArgumentParser(
        description="Format a message to route a request to the appropriate queue",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument("queue", type=str, help="The queue to route the request to")
    parser.add_argument("reason", type=str, help="The reason for the request", nargs="*")
    parser.add_argument("-d", "--debug", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    return args


def message_builder(
        queue: str,
        route_reason: str = "",
        teams_url: str = "https://teams.microsoft.com/l/chat/0/0?users=u1377551@umail.utah.edu",
        image_url: str = "https://www.logo.wine/a/logo/Microsoft_Teams/Microsoft_Teams-Logo.wine.svg",
        image_width: int = 30,
        image_height: int = 20
    ) -> str:
    """
    Builds a message with routing information and a Teams link.

    Look at [this link](https://mcgill.service-now.com/itportal?id=kb_article_view&sysparm_article=KB0012134) for more information on the formatting of the teams link.

    Args:
        queue (str): The name of the queue to route to.
        route_reason (str, optional): The reason for routing. Defaults to "".
        teams_url (str, optional): The URL of the Teams chat. Defaults to "https://teams.microsoft.com/l/chat/0/0?users=u1377551@umail.utah.edu".
        image_url (str, optional): The URL of the Teams logo image. Defaults to "https://www.logo.wine/a/logo/Microsoft_Teams/Microsoft_Teams-Logo.wine.svg".
        image_width (int, optional): The width of the Teams logo image. Defaults to 30.
        image_height (int, optional): The height of the Teams logo image. Defaults to 20.

    Returns:
        str: The formatted message with routing information and a Teams link.
    """
    if route_reason:
        route_reason = f"<br><strong>Reason:</strong> {route_reason}"
    return f"""[code]<div>
<pre style="display: inline-block;"><strong>Routing to:</strong> {queue}{route_reason}</pre>
<p>If routed incorrectly please advise.<br>
Message me on <a style="text-decoration:underline" href="{teams_url}" target="_blank" rel="noopener noreferrer">Teams<img src="{image_url}" width="{image_width}" height="{image_height}" alt="Microsoft Teams Logo"/></a></p>
</div>[/code]"""


def queue_search(query: str) -> str:
    full_queue_names: list[str] = [
        "ITS - CTO - Field Services",
        "ITS - CTO - Service Desk",
        "UIT - NCI - Network - Automation",
        "UIT - NCI - Campus Computer Support (UCCS)",
        "UIT - NCI - Network - Core/Data Center",
        "UIT - NCI - Network - DDI",
        "UIT - NCI - Network - Edge",
        "UIT - NCI - Network - Engineering",
        "UIT - NCI - Network - Firewall/VPN",
        "UIT - NCI - Network - Load Balancer",
        "UIT - NCI - Network - Wireless",
        "UIT - NCI - Telephone technicians",
        "UIT - NCI - Fiber Installers",
        "UIT - NCI - Cable Technicians",
        "UIT - ISO - IAM (Identity and Access Mgmt)",
        "UIT - NCI - UMail & Collaboration",
        "CTO - Biomed",
        "Storage Management Services and Backup (SMS)",
        "Other"  # This is a placeholder for a custom queue name
    ]
    alt_queue_names: dict[str, str] = {
        "fs": "ITS - CTO - Field Services",
        "toast": "UIT - NCI - Network - Automation",
        "infoblox": "UIT - NCI - Network - DDI",
        "fw": "UIT - NCI - Network - Firewall/VPN",
        "lb": "UIT - NCI - Network - Load Balancer",
        "wifi": "UIT - NCI - Network - Wireless",
        "voip": "UIT - NCI - Telephone technicians",
    }

    fs = FuzzySet(full_queue_names + list(alt_queue_names.keys()))

    match = fs.get(query)[0]  # Get the best match for the query

    if not match:
        log.error(f"Could not find a match for '{query}'")
        return None
    
    log.debug(f"Match: {match}")

    match = match[1]

    if match in alt_queue_names:  # If the match is an alternate queue name, return the full queue name
        return alt_queue_names[match]
    
    if match == "Other":  # If the match is "other", ask the user for the queue name
        return Prompt.ask("What's the queue name?")

    return match  # Otherwise, return the full queue name


def main_v3() -> None:
    """
    This function routes the request to the appropriate queue based on the provided arguments.

    Args:
        None

    Returns:
        None
    """
    from nrc import ansi
    teams_logo = '<img src="https://www.logo.wine/a/logo/Microsoft_Teams/Microsoft_Teams-Logo.wine.svg" width="30" height="20" alt="Microsoft Teams Logo"/>'
    teams_url = 'https://teams.microsoft.com/l/chat/0/0?users=u1377551@umail.utah.edu'
    teams_me_link = f'[code]<u><a href="{teams_url}" target="_blank" rel="noopener noreferrer">Teams {teams_logo}</a></u>[/code]'
    advice_text = f"If routed incorrectly please advise.\nMessage me on {teams_me_link}"

    queue_mapping = {  # This is a mapping of the queue name to the actual queue name
        "field services": "ITS - CTO - Field Services",
        "fs": "ITS - CTO - Field Services",
        "automation": "UIT - NCI - Network - Automation",
        "toast": "UIT - NCI - Network - Automation",
        "uccs": "UIT - NCI - Campus Computer Support (UCCS)",
        "computer support": "UIT - NCI - Campus Computer Support (UCCS)",
        "core": "UIT - NCI - Network - Core/Data Center",
        "data center": "UIT - NCI - Network - Core/Data Center",
        "ddi": "UIT - NCI - Network - DDI",
        "infoblox": "UIT - NCI - Network - DDI",
        "edge": "UIT - NCI - Network - Edge",
        "engineering": "UIT - NCI - Network - Engineering",
        "firewall": "UIT - NCI - Network - Firewall/VPN",
        "fw": "UIT - NCI - Network - Firewall/VPN",
        "vpn": "UIT - NCI - Network - Firewall/VPN",
        "lb": "UIT - NCI - Network - Load Balancer",
        "load balancer": "UIT - NCI - Network - Load Balancer",
        "load_balancer": "UIT - NCI - Network - Load Balancer",
        "loadbalancer": "UIT - NCI - Network - Load Balancer",
        "wireless": "UIT - NCI - Network - Wireless",
        "wifi": "UIT - NCI - Network - Wireless",
        "wi-fi": "UIT - NCI - Network - Wireless",
        "phone": "UIT - NCI - Telephone technicians",
        "telephone": "UIT - NCI - Telephone technicians",
        "voip": "UIT - NCI - Telephone technicians",
        "fiber": "UIT - NCI - Fiber Installers",
        "cable": "UIT - NCI - Cable Technicians",
        "cable team": "UIT - NCI - Cable Technicians",
        "cable tech": "UIT - NCI - Cable Technicians",
        "cable techs": "UIT - NCI - Cable Technicians",
        "cable technicians": "UIT - NCI - Cable Technicians",
        "iam": "UIT - ISO - IAM (Identity and Access Mgmt)",
        "iso": "UIT - ISO - IAM (Identity and Access Mgmt)",
        "access management": "UIT - ISO - IAM (Identity and Access Mgmt)",
        "identity and access management": "UIT - ISO - IAM (Identity and Access Mgmt)",
        "umail": "UIT - NCI - UMail & Collaboration",
        "biomed": "CTO - Biomed"
    }

    arguments = get_args()

    if arguments.debug:  # If debug is enabled, print some debug info
        arguments.queue, arguments.reason = ["uccs", "TEST"]

    requested_queue = queue_mapping.get(arguments.queue.lower(), None)
    # Get the actual queue name from the mapping or ask the user for it

    if not requested_queue:  # If the user didn't provide a valid queue name
        print(f"{ansi.red_fg}Invalid queue name{ansi.default_fg}")
        print("Valid queue names are:")
        for queue in sorted(set(queue_mapping.values())):
            print(f"    {queue}")
        print("Or provide a custom queue name.")
        requested_queue = Prompt.ask("What's the queue name?")

    route_reason = f"<br><strong>Reason:</strong> {' '.join(arguments.reason)}" if arguments.reason else ""
    # If the user provided a reason, add it to the message

    routing_message = f'[code]<pre style="display: inline-block;"><strong>Routing to:</strong> {requested_queue}{route_reason}</pre>[/code]\n{advice_text}'
    # This is the message that will be sent to the user

    pc.copy(routing_message)  # Copy the message to the clipboard

    print(f"\n\n{routing_message}\n\n{ansi.yellow_fg}This has also been added to the clipboard{ansi.default_fg}")
    # Print the message to the user and tell them it's been copied to the clipboard

    if arguments.debug:  # If debug is enabled, print some debug info
        print(f"{requested_queue=} {route_reason=} {len(arguments)=}")  # Print the debug info


def main_v4() -> None:
    """
    This function routes the request to the appropriate queue based on the provided arguments.

    Args:
        None

    Returns:
        None
    """
    ARGS = get_args()

    if ARGS.debug:  # If debug is enabled, print some debug info
        log.setLevel(logging.DEBUG)

    queue = queue_search(ARGS.queue)

    if not queue:
        #TODO: Add better error handling
        # Maybe use a for loop to ask the user for the queue name a few times
        # If they don't provide a valid queue name after a few tries, exit the script
        exit(EXIT_INVALID_ARGUMENT)

    message = message_builder(queue, " ".join(ARGS.reason))

    pc.copy(message)

    log.debug(message)
    rprint(f"[bold]Routing to:[/bold] [green]{queue}[/green]")
    if ARGS.reason:  # If the user provided a reason, print it
        rprint(f"[bold]Reason:[/bold] [green]{' '.join(ARGS.reason)}[/green]")
    rprint("[yellow]Output copied to clipboard")


if __name__ == "__main__":
    try:
        main_v4()
    except KeyboardInterrupt:
        log.info("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        log.exception(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
