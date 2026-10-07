import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PPPoETest(unittest.TestCase):
    def validate(self, enabled, account="", password=""):
        source = (ROOT / ".github/workflows/build-rockchip-25.12.x.yml").read_text()
        script = source.split("      - name: Validate PPPoE Inputs\n        run: |\n", 1)[1]
        script = textwrap.dedent(script.split("\n      - name:", 1)[0])
        with tempfile.TemporaryDirectory() as directory:
            event = Path(directory) / "event.json"
            event.write_text(json.dumps({"inputs": {
                "enable_pppoe": enabled, "pppoe_account": account,
                "pppoe_password": password,
            }}))
            return subprocess.run(["bash", "-e", "-c", script],
                                  env={**os.environ, "GITHUB_EVENT_PATH": str(event)},
                                  capture_output=True, text=True)

    def test_mode_only_and_complete_credentials_are_valid(self):
        for enabled, account, password in [("yes", "", ""),
                                            ("yes", "sample", "sample-password"),
                                            ("no", "", "")]:
            with self.subTest(enabled=enabled, account=account):
                result = self.validate(enabled, account, password)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_partial_credentials_are_rejected(self):
        for account, password in [("sample", ""), ("", "sample-password")]:
            with self.subTest(account=account):
                self.assertNotEqual(self.validate("yes", account, password).returncode, 0)

    def configure(self, account="", password=""):
        source = (ROOT / "files/etc/uci-defaults/99-custom.sh").read_text()
        script = source.split("    # PPPoE设置\n", 1)[1].split("\n    uci commit network", 1)[0]
        script = 'uci() { printf "%s\\n" "$*"; };\n' + script
        return subprocess.run(["sh", "-e", "-c", script],
                              env={**os.environ, "LOGFILE": "/dev/null",
                                   "enable_pppoe": "yes", "pppoe_account": account,
                                   "pppoe_password": password},
                              capture_output=True, text=True, check=True).stdout

    def test_mode_only_preserves_restored_credentials(self):
        commands = self.configure()
        self.assertIn("set network.wan.proto=pppoe", commands)
        self.assertNotIn("network.wan.username", commands)
        self.assertNotIn("network.wan.password", commands)

    def test_explicit_credentials_are_applied(self):
        commands = self.configure("sample", "sample-password")
        self.assertIn("set network.wan.username=sample", commands)
        self.assertIn("set network.wan.password=sample-password", commands)


if __name__ == "__main__":
    unittest.main()
