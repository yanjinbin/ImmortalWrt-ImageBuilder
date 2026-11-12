from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
NETWORK_DEFAULTS = ROOT / "files/etc/uci-defaults/99-network-tuning.sh"


class ProxyNetworkTuningTest(unittest.TestCase):
    """Transparent proxy (TPROXY) needs flow offloading off and no duplicate DNS hijack."""

    def setUp(self):
        self.script = NETWORK_DEFAULTS.read_text(encoding="utf-8")

    def test_script_is_executable(self):
        self.assertTrue(NETWORK_DEFAULTS.stat().st_mode & 0o111)

    def test_skips_when_nikki_is_absent(self):
        self.assertIn("uci -q get nikki", self.script)

    def test_disables_flow_offloading(self):
        self.assertIn("uci set firewall.@defaults[0].flow_offloading='0'", self.script)
        self.assertIn("uci set firewall.@defaults[0].flow_offloading_hw='0'", self.script)

    def test_disables_dnsmasq_redirect(self):
        self.assertIn('.dns_redirect=\'0\'', self.script)
        self.assertIn("uci commit dhcp", self.script)

    def test_caps_dns_cache_ttl(self):
        self.assertIn(".min_cache_ttl='300'", self.script)

    def test_clears_stale_connections_on_reload(self):
        self.assertIn("uci set nikki.procd.fast_reload='0'", self.script)
        self.assertIn("uci set nikki.procd.clear_connections_on_reload='1'", self.script)


if __name__ == "__main__":
    unittest.main()
