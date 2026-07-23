import asyncio
import unittest

from core.config import VERSION as CONFIG_VERSION
from core.system.doctor import VERSION as DOCTOR_VERSION
from main_api import app, root


class VersionConsistencyTests(unittest.TestCase):
    def test_config_version(self):
        self.assertEqual(CONFIG_VERSION, "4.1.0")

    def test_doctor_version(self):
        self.assertEqual(DOCTOR_VERSION, "4.1.0")

    def test_config_and_doctor_versions_match(self):
        self.assertEqual(CONFIG_VERSION, DOCTOR_VERSION)

    def test_api_identity(self):
        self.assertEqual(app.title, "Atlas API v4.1")
        self.assertEqual(asyncio.run(root())["version"], "4.1.0")


if __name__ == "__main__":
    unittest.main()
