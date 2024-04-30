#!/usr/bin/env python3
from SwitchInfo import Switch
from nrc import argumentToVariable

reset = '\033[0m'
purple = '\033[35m'
light_blue = '\033[36m'
green = '\033[1;32m'


def clear_two_lines_up():
    """
    Clears two lines above the current cursor position in the terminal.
    """
    print('\033[1A\033[2K\033[1A\033[2K', end='', flush=True)


def clear_one_line_up():
    """
    Clears one line above the current cursor position in the terminal.
    """
    print('\033[1A\033[2K', end='', flush=True)


switch = Switch(argumentToVariable(1, prompt_text='Switch Address: '))
uptime = switch.uptime
print(f'{light_blue}The switch {purple}[{reset}{green}{switch.ip}{reset}{purple}]{reset} {light_blue}has '
    f'been up for{reset} {purple}[{reset}{green}{uptime[0]}{reset}{purple}]{reset} '
    f'{light_blue}days which means the date it was '
    f'restarted was{reset} {purple}[{reset}{green}{uptime[1].format("ddd, MMM D YYYY [a]t, h:mm A")}{reset}{purple}]{reset} ')
