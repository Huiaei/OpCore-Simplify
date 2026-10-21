import os
import subprocess
import unittest
from unittest.mock import patch

from Scripts.utils import Utils


class TestOpenFolder(unittest.TestCase):
    """Opening the results folder must never abort a finished build."""

    def test_missing_opener_is_swallowed(self):
        u = Utils()
        with patch("subprocess.run", side_effect=FileNotFoundError("xdg-open")):
            with patch("os.name", "posix"):
                with patch("os.uname") as uname:
                    uname.return_value.sysname = "Linux"
                    # Must not raise.
                    u.open_folder("/tmp")

    def test_subprocess_error_is_swallowed(self):
        u = Utils()
        with patch("subprocess.run", side_effect=subprocess.SubprocessError("boom")):
            with patch("os.name", "posix"):
                with patch("os.uname") as uname:
                    uname.return_value.sysname = "Linux"
                    u.open_folder("/tmp")

    def test_macos_uses_open(self):
        u = Utils()
        with patch("subprocess.run") as run:
            with patch("os.name", "posix"):
                with patch("os.uname") as uname:
                    uname.return_value.sysname = "Darwin"
                    u.open_folder("/tmp")
        run.assert_called_once_with(["open", "/tmp"])

    def test_linux_uses_xdg_open(self):
        u = Utils()
        with patch("subprocess.run") as run:
            with patch("os.name", "posix"):
                with patch("os.uname") as uname:
                    uname.return_value.sysname = "Linux"
                    u.open_folder("/tmp")
        run.assert_called_once_with(["xdg-open", "/tmp"])


if __name__ == "__main__":
    unittest.main()
