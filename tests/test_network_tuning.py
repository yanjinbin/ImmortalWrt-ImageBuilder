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

    def test_clears_dns_fallback_through_mixin(self):
        # DoT fallback keeps failing through the proxy node; nameserver-policy already splits.
        self.assertIn("network-tuning: dns profile", self.script)
        self.assertIn("  fallback: []", self.script)
        self.assertIn("uci set nikki.mixin.mixin_file_content='1'", self.script)
        # appending must be idempotent
        self.assertIn('! grep -q "network-tuning: dns profile"', self.script)

    def test_dns_profile_uses_domestic_servers_only(self):
        self.assertIn("- 119.29.29.29", self.script)
        self.assertIn("- https://doh.pub/dns-query", self.script)
        self.assertIn("geosite:geolocation-!cn:", self.script)
        # 第三方 DoH 实测 800ms，不再写进 proxy-server-nameserver
        self.assertNotIn("sh.dns44.cn", self.script)

    def test_enforces_lan_pure_ipv4_and_disables_delegation(self):
        # 局域网终端纯 IPv4 出口，避免双栈 Happy Eyeballs 黑洞
        self.assertIn("uci -q delete network.lan.ip6assign", self.script)
        self.assertIn("uci set network.lan.delegate='0'", self.script)
        self.assertIn("uci set \"dhcp.${section}.ra='disabled'\"", self.script)
        self.assertIn("uci set \"dhcp.${section}.dhcpv6='disabled'\"", self.script)
        self.assertIn("uci commit network", self.script)

    def test_disables_nikki_lan_ipv6_proxy(self):
        # 关闭 nikki 局域网 IPv6 透明代理，避免被规则首行 IP-CIDR6,::/0,REJECT 拦截
        self.assertIn("uci set nikki.proxy.ipv6_proxy='0'", self.script)
        self.assertIn("uci set nikki.proxy.ipv6_dns_hijack='0'", self.script)

    def test_prepends_wechat_and_tencent_direct_rules(self):
        # 预置置顶微信与腾讯直连规则，防止第三方去广告规则误杀微信传图
        self.assertIn("matcher='wechat'", self.script)
        self.assertIn("matcher='tencent'", self.script)
        self.assertIn("uci set nikki.@rule[-1].node='DIRECT'", self.script)


if __name__ == "__main__":
    unittest.main()
