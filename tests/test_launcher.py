import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from widgets.fence import open_path


class TestLauncher(unittest.TestCase):
    def test_open_path_uses_item_folder_as_working_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, "run.bat")
            with open(script_path, "w", encoding="utf-8") as handle:
                handle.write("@echo off\n")

            with patch("widgets.fence._shell_execute", return_value=42) as shell_execute:
                open_path(script_path)

            shell_execute.assert_called_once_with(script_path, temp_dir)

    def test_open_path_reports_missing_files(self):
        missing_path = os.path.join(tempfile.gettempdir(), "missing-mydesktop-item.bat")
        with self.assertRaises(FileNotFoundError):
            open_path(missing_path)


if __name__ == "__main__":
    unittest.main()
