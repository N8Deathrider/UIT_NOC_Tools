#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Written by Nathan Cable - u1377551 - 08/10/2022

This script contains various styling functions used in the UIT (University Information Technology) for handling ticket notes.
"""

# Standard libraries
import argparse
import re
from csv import reader as csv_reader
from sys import exit

# Third-party libraries
import arrow
from netaddr import EUI
from netaddr import core
from netaddr import mac_cisco
import pyperclip as pc
from rich_argparse import RichHelpFormatter
from rich.console import Console
from rich.table import Table

# Local libraries
from SwitchInfo import Switch
from SwitchInfo.Switch import vlan_info
from nrc import ansi
from nrc import clear


# Standard exit codes
EXIT_SUCCESS = 0  # No errors
EXIT_GENERAL_ERROR = 1  # General error
EXIT_INVALID_ARGUMENT = 120  # Invalid argument to exit
EXIT_KEYBOARD_INTERRUPT = 130  # Keyboard interrupt (Ctrl+C)


#############
# VARIABLES #
#############
O = ansi.forgroundRGB(209,154,102)  # Orange
B = ansi.forground256(33)  # Blue
R = ansi.default_fg
BOLD_ON = ansi.bold_on
BOLD_OFF = ansi.bold_off
log_message = "The log is below."
info_tag = f"{B}[i]{R}"
stop_listening_instructions = f"{info_tag} When done, press {BOLD_ON}Enter{BOLD_OFF} and then press {BOLD_ON}Ctrl{BOLD_OFF} + {BOLD_ON}d{BOLD_OFF}"
copied_announcement = f'{ansi.yellow_fg}This has been automatically copied to the clipbord!{ansi.default_fg}'
opening_code_tag = '<code style="background-color: #dddbdb; user-select: all">'
wrapped_styled_text = None
colors = {
    "emergency": "#e0948a",
    "alert": "#ed9570",
    "critical": "#f4af6c",
    "error": "#fbc968",
    "warning": "#e8d36b",
    "notice": "#b7cb75",
    "informational": "#87c37f",
    "debug": "#57bb8a",
    "up": "#72f54a",
    "down": "#ea3323"
}
output_highlighting = [
    [r"%\w+-0-\w+(?=:)", colors["emergency"], "Emergency"],
    [r"%\w+-1-\w+(?=:)", colors["alert"], "Alert"],
    [r"%\w+-2-\w+(?=:)", colors["critical"], "Critical"],
    [r"%\w+-3-\w+(?=:)", colors["error"], "Error"],
    [r"%\w+-4-\w+(?=:)", colors["warning"], "Warning"],
    [r"%\w+-5-\w+(?=:)", colors["notice"], "Notice"],
    [r"%\w+-6-\w+(?=:)", colors["informational"], "Informational"],
    [r"%\w+-7-\w+(?=:)", colors["debug"], "Debug"],
    [r"\b(Gi|GigabitEthernet)\d+\/([01]\/)?\d{1,2}\b", "#5ab8d4", "GigabitEthernet"],
    [r"\b(Tw|TwoGigabitEthernet)\d+\/([01]\/)?\d{1,2}\b", "#56e2db", "TwoGigabitEthernet"],
    [r"\b(Te|TenGigabitEthernet)\d+\/([01]\/)?\d{1,2}\b", "#4b40e0", "TenGigabitEthernet"],
    [r"\b(Fo|FortyGigabitEthernet)\d+\/([01]\/)?\d{1,2}\b", "#ff8ad8", "FortyGigabitEthernet"],
    [r"\b(Ap|AppGigabitEthernet)\d+\/([01]\/)?\d{1,2}\b", "#ff569e", "AppGigabitEthernet"],
    [r"\b(Twe|TwentyFiveGigE)\d+\/([01]\/)?\d{1,2}\b", "#942193", "TwentyFiveGigE"],
    [r"\b(Hu|HundredGigE)\d+\/([01]\/)?\d{1,2}\b", "#d783ff", "HundredGigE"],
    [r"\b(Fa|FastEthernet)\d+\b", "#006699", "FastEthernet"],
    [r"\b(Po|Port-channel)\d{1,3}\b", "#af39ee", "Port-channel"],
    [r"\b(Vl|Vlan|VLAN|vlan )\d+\b", "#009966", "Vlan"],
    [r"(?!reliability 255\/255)(reliability \d{1,3}\/255)", colors["alert"], "Reliability"],
    [r"(?!0 (in|out)put errors)(\d+ (in|out)put errors)", colors["error"], "Input/Output Errors"],
    [r"(?!0 CRC)(\d+ CRC)", colors["error"], "CRC"],
    [r"(?!0 collisions)(\d+ collisions)", colors["warning"], "Collisions"],
    [r"(?!Total output drops: 0)(Total output drops: \d+)", colors["warning"], "Output Drops"],
    [r"(\d+ interface resets)", colors["notice"], "Interface Resets"],
    [r"(\d+ packets (in|out)put, \d+ bytes)", colors["informational"], "Packets"],
    [r"(?!0 unknown protocol drops)(\d+ unknown protocol drops)", colors["notice"], "Unknown Protocol Drops"],
    [r"(\(connected\)|\s{2}connected)", colors["up"], "Connected"],
    [r"(\(notconnect\)|\s{2}notconnect)", colors["down"], "Not Connected"],
    [r"((?<=is\s)up|connected(?=\s{4})|(?<=\()connected(?=\))|(?<=to\s)up)", colors["up"], "Up"],
    [r"((?<=is\s)administratively down|down|notconnect|disabled(?=\s{3})|(?<=\()notconnect|disabled(?=\)))", colors["down"], "Down"],
    # [r"", colors[], ""],
]


#########################
# THE STYLING FUNCTIONS #
#########################
def style_italic(text: str) -> str:
    return f"<em>{text}</em>"


def style_underline(text: str) -> str:
    return f"<u>{text}</u>"


def style_bold(text: str) -> str:
    return f"<strong>{text}</strong>"


def style_mark(text: str) -> str:
    return f"<mark>{text}</mark>"


def style_code(text: str) -> str:
    return f"{opening_code_tag}{text}</code>"


def style_vlan_information(vlan_number: str, switch: str) -> str:
    vlan_data = vlan_info(Switch(switch), vlan_number)
    return f"{opening_code_tag}{vlan_data['vlan_id']}</code> - {opening_code_tag}{vlan_data['name']}</code>"


def style_switch_information(switch_address: str) -> str:
    switch = Switch(switch_address)
    return f"{opening_code_tag}{switch.fqdn}</code> (IP: {opening_code_tag}{switch.ip}</code>)"


def style_switch_port(sp: str, switch: str) -> str:
    """
    sp stands for switchport
    switch stands for either the switch hostname or switch ip
    """
    return f"switchport {opening_code_tag}{sp}</code> of the switch {style_switch_information(switch)}"


def style_switch_port_config(sp: str, switch: str, vlan_number: str) -> str:
    """
    sp stands for switchport
    switch stands for either the switch hostname or switch ip
    """
    return f'I configured {style_switch_port(sp, switch)} to be on VLAN {style_vlan_information(vlan_number, switch)}. {log_message}\n\n\n{style_switch_output()}'


def style_patched_port_to(pp_port_number:str, sp:str, switch: str) -> str:
    return f"I patched the patch-panel port {opening_code_tag}{pp_port_number}</code> to {style_switch_port(sp, switch)}"


def style_patch_panel_port_config(pp_port_number: str, sp: str, switch: str, vlan_number: str) -> str:
    return f"I patched the patch-panel port {opening_code_tag}{pp_port_number}</code> to {style_switch_port(sp, switch)} and configured that switchport to be on VLAN {style_vlan_information(vlan_number, switch)}. {log_message}\n\n\n{style_switch_output()}"


def style_switch_output(switch_output: str = pc.paste()) -> str:
    """
    Styles the switch output by wrapping it in a pre tag, converting
    newlines into <br>, and highlighting certain things like
    interface names, vlan numbers, and vlan names.

    Args:
        switch_output (str, optional): The switch output to be styled. Defaults to pc.paste().

    Returns:
        str: The styled switch output.
    """
    # o = []
    # print(f"Please paste the copy of the switch output here.\n{stop_listening_instructions}")
    # while True:
    #     try:
    #         o.append(input())
    #     except EOFError:
    #         break
    # clear()
    # output = f"<pre>{'<br>'.join(pc.paste().splitlines())}</pre>"
    switch_output = syntax_highlighting(
        f"<pre style=\"background-color: #1e2021;color: #b9b3aa;width: fit-content; max-width: 100%\">{'<br>'.join(switch_output.splitlines())}</pre>"
    )
    return switch_output


def style_email() -> str:
    """
    em is short for email
    """
    styles = [
        ["From:", "<strong>From:</strong>"],
        ["Date:", "<strong>Date:</strong>"],
        ["Sent:", "<strong>Sent:</strong>"],
        ["To:", "<strong>To:</strong>"],
        ["Cc:", "<strong>Cc:</strong>"],
        ["Subject:", "<strong>Subject:</strong>"]
    ]
    styled_email = "<br>".join(pc.paste().splitlines())
    for style in styles:
        styled_email = styled_email.replace(*style)
    return f"<pre>{styled_email}</pre>"


def style_teams() -> str:
    return teams_html_gen(messages_text=pc.paste())


def style_link(t: str, u: str) -> str:
    """
    t is short for text
    u is short for url
    """
    return f'<a href="{u}" target="_blank" rel="noopener noreferrer">{t}</a>'


def style_host_record(ip: str, mac: str, fqdn: str) -> str:
    """IP assignment request template

    :param ip: IP address
    :type ip: str
    :param mac: MAC address
    :type mac: str
    :param fqdn: Fully Qualified Domain Name
    :type fqdn: str
    :return: Completed template
    :rtype: str
    """
    return f"The IP address {ip} should now be reserved for MAC address {mac} under {fqdn} in Infoblox"


def style_change_type(reference_number: str) -> str:
    return f"Thank you for reaching out to us. After carefully reviewing your ticket, it appears that this ticket is currently categorized as the incorrect type for your request. \
To ensure proper handling and alignment with our processes, I will be closing this ticket and creating a new one under the appropriate category.\n\n\
In our system, \"Incidents\" are primarily intended for reporting issues or problems, while \"Tasks/Requests\" are more suitable for requesting new services or actions.\n\n\
The new ticket number is {reference_number}"


def style_ap() -> str:
    return "Hello,\n\nI would like to inform you that the ports at the bottom of the access point in your room are now active."


def style_dup(ticket) -> str:
    return f"It appears that this is a duplicate ticket of {ticket}. I will proceed to close this duplicate ticket and continue the ongoing work within the original ticket, {ticket}."


def style_csv() -> str:
    table_string = csv_to_table(pc.paste())
    return f"<pre>{'<br>'.join(table_string.splitlines())}</pre>"


def style_toast_output() -> str:
    output = f"<pre style=\"background-color: #1e2021;color: #b9b3aa;width: fit-content;\">{'<br>'.join(pc.paste().splitlines())}</pre>"
    return output


def style_slow_connection() -> str:
    message: str = "Hello, to troubleshoot a slow connection, we will need a few things.\n\n"
    required_info: list = [
        "The MAC address and IP address of a device experiencing the issue. How to find your MAC address: https://uofu.service-now.com/it?id=uu_kb_article&sys_id=bcc37bb2131f53843c69d7028144b077",
        "The website / destination you're trying to visit that is slow or not working.",
        "How the device is connected to the University of Utah network. (wired, wireless, VPN, etc.)",
        "How long this issue has been going on.",
        "The results of visiting https://speedtest.uen.net and running a speed test.",
        "What kind of device is experiencing this issue.",
        "Details of any troubleshooting steps already taken along with their outcomes.",
        "Any other details."
    ]
    for number, info in enumerate(required_info, start=1):
        message += f"{number}) {info}\n"
    return message


def style_mac(mac: str) -> str:
    try:
        mac_address: EUI = EUI(mac)
    except core.AddrFormatError:
        return mac
    else:
        mac_address.dialect = mac_cisco
        return str(mac_address)


def style_wrong_ticket(created_type: str, ticket_name: str, ticket_link: str) -> str:
    return f"""Hello, for this, you will need to create a "{ticket_name}" ticket instead of a "{created_type}". This ensures that all the necessary information is included and the ticket gets sent to the correct team or teams.
To create a "{ticket_name}", please visit https://orderit.utah.edu and then on that page select "Service Catalog". On the next page, select the tab labeled "A-Z Index" and then select the "{ticket_name.upper()[0]}" section. Under that section you should see an option for "{ticket_name}".

Alternatively, you can follow this link:
{ticket_link}"""


###################
# OTHER FUNCTIONS #
###################


def get_args() -> argparse.Namespace:
    """
    Parse command line arguments and return the parsed arguments as a Namespace object.

    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    p = argparse.ArgumentParser(
        description="The point of this script is to make it slightly more convenient to add style to work notes.",
        formatter_class=RichHelpFormatter,
    )
    g = p.add_mutually_exclusive_group(required=True)

    p.add_argument("-d", "--debug", action="store_true")  # DEBUG

    g.add_argument(  # Italic
        "-i", nargs="+", metavar=f"{O}text{R}", help="italic: italicizes the text"
    )

    g.add_argument(  # Underline
        "-u", nargs="+", metavar=f"{O}text{R}", help="underline: underlines the text"
    )

    g.add_argument(  # Bold
        "-b", nargs="+", metavar=f"{O}text{R}", help="bold: bolds the text"
    )

    g.add_argument(  # Mark
        "-m", nargs="+", metavar=f"{O}text{R}", help="mark: marks/highlights the text"
    )

    g.add_argument(  # Code
        "-c",
        nargs="+",
        metavar=f"{O}text{R}",
        help="code: styles the text as code but what that looks like depends on the css where this text is placed",
    )

    g.add_argument(  # Vlan Info
        "-vi",
        nargs=2,
        metavar=(f"{O}vlan_number{R}", f"{O}switch_ip{R}|{O}switch_name{R}"),
        help=f"vlan information: styles the string as '{O}{{vlan_number}}{R} - {O}{{vlan_description}}{R}' with both the vlan number and name wrapped with code tags",
    )

    g.add_argument(  # Switch Info
        "-si",
        nargs=1,
        metavar=f"{O}switch_ip{R}|{O}switch_name{R}",
        help="switch information: takes either the hostname or ip address and returns '{O}{{hostname}}{R} (IP: {O}{{switch_ip}}{R})' with both the hostname and ip address wrapped with the code tags",
    )

    g.add_argument(  # Switch-port
        "-sp",
        nargs=2,
        metavar=(f"{O}switch_interface{R}", f"{O}switch_ip{R}|{O}switch_name{R}"),
        help=f"switch port: styles the string as 'switchport {O}{{switch_interface}}{R} of {O}{{switch_name}}{R} (IP: {O}{{switch_ip}}{R})' with the information (highlighted with orange) being wrapped in code tags",
    )

    g.add_argument(  # Switch-port Config
        "-spc",
        nargs=3,
        metavar=(
            f"{O}switch_interface{R}",
            f"{O}switch_ip{R}|{O}switch_name{R}",
            f"{O}vlan_number{R}",
        ),
        help=f"switchport config: styles the string to match 'I configured switchport {O}{{switch_interface}}{R} of switch {O}{{switch_name}}{R} (IP: {O}{{switch_ip}}{R}) to be on VLAN {O}{{vlan_number}}{R} - {O}{{vlan_description}}{R}. The log is below.' with the information (highlighted with orange) being wrapped with code tags",
    )

    g.add_argument(  # Patched Port To
        "-ppt",
        nargs=3,
        metavar=(
            f"{O}patch_panel_port_number{R}",
            f"{O}switch_interface{R}",
            f"{O}switch_ip{R}|{O}switch_name{R}",
        ),
        help=f"patched port to: styles the string as 'I patched the patch-panel port {O}{{patch_panel_port_number}}{R} to switchport {O}{{switch_interface}}{R} of switch {O}{{switch_name}}{R} (IP: {O}{{switch_ip}}{R})' with all of the information (highlighted with orange) being wrapped in code tags",
    )

    g.add_argument(  # Patch-panel Port Config
        "-ppc",
        nargs=4,
        metavar=(
            f"{O}patch_panel_port_number{R}",
            f"{O}switch_interface{R}",
            f"{O}switch_ip{R}|{O}switch_name{R}",
            f"{O}vlan_number{R}",
        ),
        help=f"patch-panel-port patch and config: styles the string as 'I patched the patch-panel port {O}{{patch_panel_port_number}}{R} to switchport {O}{{switch_interface}}{R} of switch {O}{{switch_name}}{R} (IP: {O}{{switch_ip}}{R}) and configured the switchport to be on VLAN {O}{{vlan_number}}{R} - {O}{{vlan_description}}{R}. The log is below.' with all of the information (highlighted with orange) being wrapped in code tags",
    )

    g.add_argument(  # Switch Output
        "-so",
        action="store_true",
        help="switch output: wraps the switch output in a pre tag and converts newlines into <br> and highlights certain things like interface names, vlan numbers, and vlan names",
    )

    g.add_argument(  # Toast Output
        "-to",
        action="store_true",
        help="Toast output: wraps the Toast output in a pre tag and converts newlines into <br>",
    )

    g.add_argument(  # Email
        "-em",
        action="store_true",
        help="email: works just like -so but will bold 'From:', 'Date:', 'To:', and 'Subject:' (the easiest way to get all of that is to click 'Reply' on the email and then copy the information from the 'previous conversation' area)",
    )

    g.add_argument(  # Teams
        "-t",
        action="store_true",
        help="teams: works just like -so but will take from your clipboard and format it like a teams convo by looking for the time stamp, name, and message body",
    )

    g.add_argument(  # ServiceNow Link
        "-l",
        "--link",
        nargs=2,
        metavar=(f"{O}text{R}", f"{O}URL{R}"),
        help=f"servicenow link: creates a hyperlink compatable with servicenow",
    )

    g.add_argument(  # Host Reservation
        "-ho",
        "--host",
        nargs=3,
        metavar=(f"{O}IP address{R}", f"{O}MAC address{R}", f"{O}FQDN{R}"),
        help=f"host reservation: template text for IP assignment requests",
    )

    g.add_argument(  # Change Ticket Type
        "-ct",
        nargs=1,
        metavar=(f"{O}New Ticket Reference Number{R}"),
        help=f"Change Ticket Type: template text for changing a ticket type",
    )

    g.add_argument(  # AP
        "-ap",
        action="store_true",
        help="ap: the copy pasta for activating ports on access points",
    )

    g.add_argument(  # Duplicate
        "-dup",
        nargs=1,
        metavar=(f"{O}Original Ticket Reference Number{R}"),
        help=f"Duplicate Ticket: template text for closing a duplicate ticket",
    )

    g.add_argument(  # CSV to Table
        "-csv", action="store_true", help="csv: converts a csv in your clipboard to a table"
    )

    g.add_argument(  # Slow Connection
        "-sc",
        action="store_true",
        help="slow connection: template text for getting required information for a slow connection ticket",
    )

    g.add_argument(  # MAC
        "-mc",
        "--mac",
        nargs=1,
        metavar=f"{O}MAC address{R}",
        help="MAC address: converts the MAC address to cisco formats and puts it in a code tag",
    )

    g.add_argument(  # Wrong Ticket
        "-wt",
        "--wrong-ticket",
        nargs=3,
        metavar=(f"{O}current_ticket_type{R}", f"{O}correct_ticket_type_name{R}", f"{O}correct_ticket_type_link{R}"),
        help="wrong ticket: template text for when tickets are created under the wrong category"
    )

    g.add_argument(  # Version
        "-v", "--version", action="version", version="%(prog)s 2.0"
    )

    return p.parse_args()


def teams_message_parser(text: str) -> list[dict]:
    """
    Parses text containing messages with timestamps and reactions into a list of dictionaries.

    Args:
        text (str): The text containing messages.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary contains keys:
            - 'timestamp' (str): The timestamp of the message.
            - 'sender' (str): The sender of the message.
            - 'message' (str): The content of the message.
            - 'reactions' (optional) (list[dict]): A list of dictionaries containing reaction info,
                with keys 'type' (str) (e.g., "like", "heart") and 'count' (int) (number of reactions).
    """
    pattern = r"\[(.+?)\]\s*(.*?)(?=\n\[|\Z)"
    matches = re.findall(pattern, text, re.DOTALL)
    messages = []
    for timestamp, sender_message in matches:
        sender, potential_message_reactions = sender_message.split("\n", 1)
        message, *reactions = potential_message_reactions.splitlines()

        # Check if reactions exist (based on starting with whitespace)
        if reactions:
            parsed_reactions = []
            for reaction_line in reactions:
                if reaction_line.startswith(" "):  # Check for leading whitespace
                    # Split on whitespace (separates multiple reaction types)
                    reaction_types_and_counts = reaction_line.strip().split()
                    for i in range(0, len(reaction_types_and_counts), 2):
                        try:
                            reaction_type, count_str = reaction_types_and_counts[
                                i : i + 2
                            ]
                            count = int(count_str)
                        except ValueError:
                            # Handle cases where count_str is not a number
                            count = 0
                        parsed_reactions.append({"type": reaction_type, "count": count})
            reactions = (
                parsed_reactions if parsed_reactions else []
            )  # Set empty list if no valid reactions found
        else:
            reactions = None

        messages.append(
            {
                "timestamp": timestamp.strip(),
                "sender": sender.strip(),
                "message": message.strip(),
                "reactions": reactions,
            }
        )
    return messages


def teams_message_text_gen(message_text: str) -> str:
    return "".join(map(lambda l: f"<p>{l}</p>".replace("\n", "<br>"), message_text.splitlines()))


def teams_message_gen(timestamp: str, name: str, message_content: str) -> str:
    if (name == "Nathan Cable"):
        message_template = """<div class="u1377551-message me"><div class="u1377551-message-head"><time>{date_time}</time><div>{name}</div></div><div class="u1377551-message-body"><div><div>{message_text}</div></div></div></div>"""
    else:
        message_template = """<div class="u1377551-message"><div class="u1377551-message-head"><div>{name}</div><time>{date_time}</time></div><div class="u1377551-message-body"><div><div>{message_text}</div></div></div></div>"""
    return message_template.format(date_time=timestamp, name=name, message_text=teams_message_text_gen(message_content))


def teams_html_gen2(messages: list) -> str:
    style = r""""""
    them_html = """<div class="message-container"><div class="message"><div style="display:flex; margin-top:10px"><div style="flex:none; overflow:hidden; border-radius:50%; height:42px; width:42px; margin:10px"><img height="42" src="{image}" style="vertical-align:top; width:42px; height:42px;" width="42"></div><div class="them" style="flex:1; overflow:hidden;"><div style="font-size:1.2rem; white-space:nowrap; text-overflow:ellipsis; overflow:hidden;"><span style="font-weight:700;">{name}</span><span style="margin-left:1rem;">{date}</span></div><div>{conversation}</div>{attachment}</div></div></div></div>"""
    me_html = """<div class="message-container"><div class="message"><div style="display:flex; margin-top:10px"><div class="me" style="flex:1; overflow:hidden;"><div style="font-size:1.2rem; white-space:nowrap; text-overflow:ellipsis; overflow:hidden;"><span style="font-weight:700;">{name}</span><span style="margin-left:1rem;">{date}</span></div><div>{conversation}</div>{attachment}</div><div style="flex:none; overflow:hidden; border-radius:50%; height:42px; width:42px; margin:10px"><img height="42" src="{image}" style="vertical-align:top; width:42px; height:42px;" width="42"></div></div></div></div>"""
    attachment_html = """<div class="attachment"><a href="{attachment_url}" target="_blank">{attachment_name}</a></div>"""


def teams_html_gen(messages_text: str) -> str:
    random_id = arrow.now("local").format("x")
    # This is just a random id to scope the css to this specific instance of the script
    
    styles = r"""\
.u1377551-messages {margin-left: 10%;margin-right: 10%;display: flex;flex-direction: column;width: 80%;padding-top: 12px;padding-bottom: 12px;}
.u1377551-messages * {-webkit-font-smoothing: antialiased;}
.u1377551-messages p {margin: 0;}
.u1377551-message {margin-bottom: 10px;max-width: 500px;}
.u1377551-message-head {margin-bottom: 2px;color: #616161;align-items: baseline;display: flex;column-gap: 8px;white-space: nowrap;line-height: 16px;font-size: 12px;}
.u1377551-message-head div {text-overflow: ellipsis;overflow-x: hidden;overflow-y: hidden;}
.u1377551-message-body {display: flex;}
.u1377551-message-body div {background-color: #ffffff;color: #242424;border-radius: 6px;border-color: transparent;border-style: solid;border-width: 1px;word-break: break-word;padding: 6px 15px 8px 15px;position: relative;line-height: 20px;font-weight: 400;font-size: 14px;font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, "Apple Color Emoji", "Segoe UI Emoji", sans-serif;text-align: start;}
.u1377551-message-body div div {overflow-x: auto;}
.u1377551-message.me {align-self: end;}
.u1377551-message.me .u1377551-message-head {justify-content: flex-end;}
.u1377551-message.me .u1377551-message-body {justify-content: flex-end;}
.u1377551-message.me .u1377551-message-body div {background-color: #E8EBFA;}
        """
    messages = []
    message_dicts = teams_message_parser(messages_text)
    for message_dict in message_dicts:
        messages.append(teams_message_gen(message_dict["timestamp"], message_dict["sender"], message_dict["message"]))
    messages = "\n".join(messages)
    return """<div style="background-color: #F5F5F5">
    <style>
        {styles}
    </style>
    <div class="u1377551-messages">
        {messages}
    </div>
</div>""".format(styles=styles, messages=messages)


def syntax_highlighting(text: str) -> str:
    for filter, color, name in output_highlighting:
        text = re.sub(filter, f"<span name=\"{name}\"style=\"color:{color};\">\\g<0></span>", text, 0, re.MULTILINE)
    return text


def csv_to_table(csv_data: str) -> str:
    csv_data = csv_reader(csv_data.splitlines())
    console = Console()

    table = Table(show_header=True, show_lines=True, header_style=None)

    # Assuming the first row is the header
    headers = next(csv_data)
    for header in headers:
        table.add_column(header)

    # Add the rest of the rows
    for row in csv_data:
        table.add_row(*row)

    # Convert the table to a string
    with console.capture() as capture:
        console.print(table)

    table_string = capture.get()

    console.print(table)

    return table_string


def sn_code_tag_wrapper(text: str) -> str:
    """
    Wraps the given text with [code] tags.

    Args:
        text (str): The text to be wrapped.

    Returns:
        str: The wrapped text.
    """
    return f"[code]{text}[/code]"


def main() -> None:
    """
    Main function that processes command line arguments and applies styling to text.

    Args:
        None

    Returns:
        None
    """
    ARGS = get_args()

    if ARGS.debug:  # DEBUG
        print(ARGS)

    wrapped_styled_text = None

    if ARGS.i:  # Italic
        styled_text = style_italic(" ".join(ARGS.i))
    elif ARGS.u:  # Underline
        styled_text = style_underline(" ".join(ARGS.u))
    elif ARGS.b:  # Bold
        styled_text = style_bold(" ".join(ARGS.b))
    elif ARGS.m:  # Mark
        styled_text = style_mark(" ".join(ARGS.m))
    elif ARGS.c:  # Code
        styled_text = style_code(" ".join(ARGS.c))
    elif ARGS.vi:  # Vlan Info
        styled_text = style_vlan_information(ARGS.vi[0], ARGS.vi[1])
    elif ARGS.si:  # Switch Info
        styled_text = style_switch_information(ARGS.si[0])
    elif ARGS.sp:  # Switch-port
        styled_text = style_switch_port(ARGS.sp[0],ARGS.sp[1])
    elif ARGS.spc:  # Switch-port Config
        styled_text = style_switch_port_config(ARGS.spc[0], ARGS.spc[1], ARGS.spc[2])
    elif ARGS.ppt:  # Patched Port To
        styled_text = style_patched_port_to(ARGS.ppt[0], ARGS.ppt[1], ARGS.ppt[2])
    elif ARGS.ppc:  # Patch-panel Port Config
        styled_text = style_patch_panel_port_config(ARGS.ppc[0], ARGS.ppc[1], ARGS.ppc[2], ARGS.ppc[3])
    elif ARGS.so:  # Switch Output
        styled_text = style_switch_output()
    elif ARGS.to:  # Toast Output
        styled_text = style_toast_output()
    elif ARGS.em:  # Email
        styled_text = style_email()
    elif ARGS.t:  # Teams
        styled_text = style_teams()
    elif ARGS.link:  # ServiceNow Link
        styled_text = style_link(ARGS.link[0], ARGS.link[1])
    elif ARGS.host:  # Host record
        wrapped_styled_text = style_host_record(ip=ARGS.host[0], mac=ARGS.host[1], fqdn=ARGS.host[2])
    elif ARGS.ct:  # Change type
        wrapped_styled_text = style_change_type(reference_number=ARGS.ct[0])
    elif ARGS.ap:  # AP
        wrapped_styled_text = style_ap()
    elif ARGS.dup:  # Duplicate
        wrapped_styled_text = style_dup(ticket=ARGS.dup[0])
    elif ARGS.csv:  # CSV to Table
        styled_text = style_csv()
    elif ARGS.sc:  # Slow Connection
        wrapped_styled_text = style_slow_connection()
    elif ARGS.mac:  # MAC
        styled_text = style_code(style_mac(ARGS.mac[0]))
    elif ARGS.wrong_ticket:  # Wrong Ticket
        wrapped_styled_text = style_wrong_ticket(ARGS.wrong_ticket[0], ARGS.wrong_ticket[1], ARGS.wrong_ticket[2])

    if not wrapped_styled_text:
        wrapped_styled_text = sn_code_tag_wrapper(styled_text)

    pc.copy(wrapped_styled_text)
    print(f"{wrapped_styled_text}\n\n{copied_announcement}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCtrl + c pressed. Exiting script...")
        exit(EXIT_KEYBOARD_INTERRUPT)
    except Exception as e:
        print(f"An unhandled error occurred: {e}")
        exit(EXIT_GENERAL_ERROR)
