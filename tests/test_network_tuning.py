from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
NETWORK_DEFAULTS = ROOT / "files/etc/uci-defaults/99-network-tuning.sh"


class ProxyNetworkTuningTest(unittest.TestCase):
    """固件只做系统层；分流/DNS 由 aliyun 订阅模板提供，不在本地重复。"""

    def setUp(self):
        self.script = NETWORK_DEFAULTS.read_text(encoding="utf-8")

    def test_script_is_executable(self):
        self.assertTrue(NETWORK_DEFAULTS.stat().st_mode & 0o111)

    def test_skips_when_nikki_is_absent(self):
        self.assertIn("uci -q get nikki", self.script)

    def test_flow_offloading_software_only(self):
        # TPROXY 命中的流量走本地协议栈、不进 forward，软件卸载不影响代理；
        # 硬件卸载会绕过 netfilter，必须保持关闭。
        self.assertIn("uci set firewall.@defaults[0].flow_offloading='1'", self.script)
        self.assertIn("uci set firewall.@defaults[0].flow_offloading_hw='0'", self.script)

    def test_rejects_lan_ipv6_egress(self):
        self.assertIn("Reject-LAN-IPv6-egress", self.script)
        self.assertIn("uci set firewall.@rule[-1].family='ipv6'", self.script)
        self.assertIn("uci set firewall.@rule[-1].target='REJECT'", self.script)
        self.assertIn("uci set firewall.@rule[-1].src='lan'", self.script)
        self.assertIn("uci set firewall.@rule[-1].dest='wan'", self.script)

    def test_disables_dnsmasq_redirect(self):
        self.assertIn('.dns_redirect=\'0\'', self.script)
        self.assertIn("uci commit dhcp", self.script)

    def test_caps_dns_cache_ttl(self):
        self.assertIn(".min_cache_ttl='300'", self.script)

    def test_clears_stale_connections_on_reload(self):
        self.assertIn("uci set nikki.procd.fast_reload='0'", self.script)
        self.assertIn("uci set nikki.procd.clear_connections_on_reload='1'", self.script)

    def test_does_not_override_subscription_dns(self):
        # DNS 已收敛到 aliyun 订阅模板（dns=split）。
        # 固件若再往 mixin.yaml 写 DNS，会覆盖订阅并重新引入 doh.pub。
        self.assertNotIn("fallback: []", self.script)
        self.assertNotIn("uci set nikki.mixin.mixin_file_content='1'", self.script)
        self.assertIn("network-tuning: dns profile", self.script)  # 仅用于清理旧块
        self.assertIn("sed -i '/^# network-tuning: dns profile$/,$d'", self.script)

    def test_enforces_lan_pure_ipv4_and_disables_delegation(self):
        # 局域网终端纯 IPv4 出口，避免双栈 Happy Eyeballs 黑洞
        self.assertIn("uci -q delete network.lan.ip6assign", self.script)
        self.assertIn("uci set network.lan.delegate='0'", self.script)
        self.assertIn("uci set \"dhcp.${section}.ra='disabled'\"", self.script)
        self.assertIn("uci set \"dhcp.${section}.dhcpv6='disabled'\"", self.script)
        self.assertIn("uci set \"dhcp.${section}.ndp='disabled'\"", self.script)
        self.assertIn("uci commit network", self.script)

    def test_disables_nikki_lan_ipv6_proxy_but_keeps_dns_hijack(self):
        # 不代理 IPv6；但 IPv6 DNS 必须继续劫持，否则终端会绕过内核直连 ISP DNS
        self.assertIn("uci set nikki.proxy.ipv6_proxy='0'", self.script)
        self.assertIn("uci set nikki.proxy.ipv6_dns_hijack='1'", self.script)

    def test_never_presets_geosite_wechat_or_tencent(self):
        # MetaCubeX 的 geosite.dat 没有 wechat/tencent 分类：
        # 写了会导致配置校验失败、mihomo 起不来。订阅里已用 RULE-SET,tencent 覆盖。
        self.assertNotIn("uci set nikki.@rule", self.script)
        self.assertNotIn("matcher='wechat'", self.script)
        self.assertNotIn("matcher='tencent'", self.script)

    def test_cleans_up_legacy_geosite_rules(self):
        self.assertIn("wechat|tencent)", self.script)
        self.assertIn('uci -q delete "nikki.${sec}"', self.script)


if __name__ == "__main__":
    unittest.main()
