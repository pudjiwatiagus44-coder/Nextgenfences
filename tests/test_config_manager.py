import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from managers.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    def test_load_config_accepts_utf8_bom(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "nextgen_config.json")
            expected = {
                "root_dir": temp_dir,
                "fences": [{"id": "abc", "title": "测试", "path": temp_dir}],
                "file_mapping": {},
                "rules": {},
            }
            with open(config_path, "w", encoding="utf-8-sig") as handle:
                json.dump(expected, handle)

            with patch.object(sys, "frozen", True, create=True), patch.object(
                sys, "executable", os.path.join(temp_dir, "NextGenFences.exe")
            ):
                manager = ConfigManager()

            self.assertEqual(manager.data["fences"][0]["id"], "abc")


if __name__ == "__main__":
    unittest.main()
