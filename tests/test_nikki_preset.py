from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "rockchip/build25.sh"
WORKFLOW = ROOT / ".github/workflows/build-rockchip-25.12.x.yml"
NIKKI_DEFAULTS = ROOT / "files/etc/uci-defaults/98-nikki.sh"
SYSCTL_DEFAULTS = ROOT / "files/etc/uci-defaults/97-sysctl-network.sh"


class NikkiPresetTest(unittest.TestCase):
    """Subscription URL comes from a repository secret, never from the repo."""

    def setUp(self):
        self.build = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_build_writes_the_url_only_when_provided(self):
        self.assertIn('if [ -n "${NIKKI_SUBSCRIPTION_URL:-}" ]; then', self.build)
        self.assertIn("/files/etc/nikki-subscription-url", self.build)
        self.assertIn("chmod 600 /home/build/immortalwrt/files/etc/nikki-subscription-url", self.build)

    def test_workflow_passes_the_secret(self):
        self.assertIn('-e NIKKI_SUBSCRIPTION_URL="${{ secrets.NIKKI_SUBSCRIPTION_URL }}"', self.workflow)

    def test_no_subscription_url_is_committed(self):
        # The bearer token must not live in the repository.
        for path in (BUILD_SCRIPT, WORKFLOW, NIKKI_DEFAULTS):
            self.assertNotIn("9fCMOiOOWX8APgRyWSbSVf", path.read_text(encoding="utf-8"))

    def test_uci_defaults_registers_subscription_and_enables_service(self):
        script = NIKKI_DEFAULTS.read_text(encoding="utf-8")
        for fragment in (
            "uci set nikki.subscription.url=\"$SUB_URL\"",
            "uci set nikki.subscription.prefer='remote'",
            "uci set nikki.config.enabled='1'",
            "uci set nikki.config.start_delay='30'",
            "/etc/init.d/nikki enable",
        ):
            self.assertIn(fragment, script)


class NikkiPresetBehaviourTest(unittest.TestCase):
    def run_script(self, url=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sub_file = root / "etc/nikki-subscription-url"
            sub_file.parent.mkdir(parents=True, exist_ok=True)
            if url is not None:
                sub_file.write_text(url + "\n")
            init = root / "etc/init.d/nikki"
            init.parent.mkdir(parents=True, exist_ok=True)
            init.write_text("#!/bin/sh\necho ENABLED\n")
            init.chmod(0o755)

            script = (NIKKI_DEFAULTS.read_text(encoding="utf-8")
                      .replace("/etc/nikki-subscription-url", str(sub_file))
                      .replace("/etc/init.d/nikki", str(init))
                      .replace("/etc/config/uci-defaults-log.txt", str(root / "log.txt")))
            runner = root / "run.sh"
            runner.write_text(
                'uci() { case "$1" in -q) return 0 ;; esac; echo "uci $*"; }\n' + script)
            out = subprocess.check_output(["sh", str(runner)], text=True, stderr=subprocess.STDOUT)
            return out, sub_file

    def test_subscription_is_written_to_uci_and_file_removed(self):
        out, sub_file = self.run_script("https://example.test/sub?token=x&dns=split")
        self.assertIn("uci set nikki.subscription.url=https://example.test/sub?token=x&dns=split", out)
        self.assertIn("uci set nikki.config.enabled=1", out)
        self.assertFalse(sub_file.exists())

    def test_service_is_enabled_without_a_url(self):
        out, sub_file = self.run_script(None)
        self.assertIn("uci set nikki.config.enabled=1", out)
        self.assertNotIn("nikki.subscription.url", out)


class GeoxBundleTest(unittest.TestCase):
    def test_asn_database_is_bundled(self):
        source = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("GeoLite2-ASN.mmdb", source)
        self.assertIn("-O \"$NIKKI_RUN_DIR/ASN.mmdb\"", source)
        self.assertIn("for f in geoip.dat geosite.dat country.mmdb ASN.mmdb; do", source)


class PacketSteeringTest(unittest.TestCase):
    def test_rps_is_enabled_at_first_boot(self):
        source = SYSCTL_DEFAULTS.read_text(encoding="utf-8")
        self.assertIn("uci set network.globals.packet_steering='1'", source)
        self.assertIn("uci set network.globals.steering_flows='16384'", source)


if __name__ == "__main__":
    unittest.main()
