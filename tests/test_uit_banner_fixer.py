import unittest
from unittest.mock import patch
from uit_banner_fixer import get_args, switch_commands_generator, get_switch_hostname
from argparse import Namespace
from netmiko import ConnectHandler

class TestGetArgs(unittest.TestCase):

    @patch("argparse.ArgumentParser.parse_args")
    def test_get_args(self, mock_parse_args):
        mock_parse_args.return_value = Namespace(
            switch_address=["192.168.0.1", "192.168.0.2"]
        )
        result = get_args()
        self.assertEqual(result.switch_address, ["192.168.0.1", "192.168.0.2"])


class TestSwitchCommandsGenerator(unittest.TestCase):

    def test_switch_commands_generator(self):
        switch_name = "Switch1"
        expected_commands = [
            "banner login ^",
            "\n",
            switch_name,
            "\n",
            "University of Utah Network:  All use of this device must comply",
            "with the University of Utah policies and procedures.  Any use of",
            "this device, whether deliberate or not will be held legally",
            "responsible.  See University of Utah Information Security",
            "Policy (4-004) for details.",
            "\n",
            "Problems within the University of Utah's network should be reported",
            "by calling the Campus Helpdesk at 581-4000, or via e-mail at",
            "helpdesk@utah.edu",
            "\n",
            "DO NOT LOGIN",
            "if you are not authorized by NetCom at the University of Utah.",
            "\n\n",
            "^",
        ]
        result = switch_commands_generator(switch_name)
        self.assertEqual(result, expected_commands)


class TestGetSwitchHostname(unittest.TestCase):

    @patch("netmiko.BaseConnection")
    def test_get_switch_hostname(self, mock_connection):
        switch_name = "Switch1"
        mock_connection.send_command.return_value = {"version": {"hostname": switch_name}}
        result = get_switch_hostname(mock_connection)
        self.assertEqual(result, switch_name)


if __name__ == "__main__":
    unittest.main()
