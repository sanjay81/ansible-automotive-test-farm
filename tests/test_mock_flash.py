import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/mock_flash.py"

class TestMockFlash(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / "firmware.img"
        self.image.write_bytes(b"MOCK_TEST_FIRMWARE\n")
        self.output = self.root / "flash.json"

    def execute(self, checksum):
        return self.execute_with(checksum, "ECU-test01")

    def execute_with(self, checksum, device):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--image", str(self.image),
                "--device", device,
                "--output", str(self.output),
                "--sha256", checksum,
            ],
            capture_output=True,
            text=True,
        )

    def test_valid_firmware(self):
        checksum = hashlib.sha256(
            self.image.read_bytes()
        ).hexdigest()

        result = self.execute(checksum)

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.output.read_text())
        self.assertEqual(
            report["status"],
            "SIMULATED_FLASH_SUCCESS",
        )
        self.assertEqual(report["device"], "ECU-test01")

    def test_invalid_checksum_rejected(self):
        result = self.execute("0" * 64)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_malformed_checksum_rejected(self):
        result = self.execute("not-a-sha256")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid SHA-256 checksum", result.stderr)
        self.assertFalse(self.output.exists())

    def test_non_simulated_device_id_rejected(self):
        checksum = hashlib.sha256(self.image.read_bytes()).hexdigest()
        result = self.execute_with(checksum, "../../dev/sda")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid device ID", result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
