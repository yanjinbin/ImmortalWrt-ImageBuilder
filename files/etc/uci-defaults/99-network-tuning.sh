#!/bin/sh
# Nikki/Mihomo 透明代理场景下的「系统层」网络基线
#
# 原则：分流规则、策略组、节点、DNS 全部来自 aliyun 订阅模板（服务端渲染）。
#       固件只写系统层，不再往 uci 里塞 mihomo 规则，避免两处配置互相打架。
#
# 1) LAN 纯 IPv4：不向终端委派 IPv6 前缀，关闭 RA / DHCPv6 / NDP。
#    终端在双栈下会并发探测 IPv6，若被 IP-CIDR6,::/0,REJECT 拦掉，
#    微信发图 / 拉取漫游记录会转圈后红叹号。WAN 侧 IPv6 完整保留，
#    仅供路由器自身连接 IPv6 节点。
# 2) Nikki 只代理 IPv4（ipv6_proxy=0）；IPv6 DNS 仍然要劫持（ipv6_dns_hijack=1），
#    否则终端的 IPv6 DNS 查询会绕过内核直连 ISP，被投毒后表现为"网站时好时坏"。
# 3) 防火墙：软件 flow offloading 开启（被 TPROXY 命中的流量走本地协议栈，
#    不进 forward，不受卸载影响），硬件 offloading 保持关闭（会绕过 netfilter）。
#    另加一条 lan→wan 的 IPv6 REJECT，兜住终端里残留的旧 v6 地址。
# 4) dnsmasq：dns_redirect=0（与 nikki 的 dport 53 -> :1053 劫持重复）。
#    LAN 的 DNS 全部被 nikki 劫持到 mihomo，dnsmasq 的缓存参数对终端无影响，不再调整。
# 5) nikki fast_reload=0 + clear_connections_on_reload=1，重载时断开僵尸连接。
# 6) 清理历史遗留：老固件写过的 GEOSITE,wechat / GEOSITE,tencent 自定义规则会让
#    配置校验直接失败（MetaCubeX 的 geosite.dat 没有这两个分类，内核起不来），
#    以及旧的 mixin DNS 覆盖块（DNS 已经收敛到订阅模板）。
#
# 幂等：只写 uci；末尾按需 reload，失败也不影响重启后生效。
LOGFILE="/etc/config/uci-defaults-log.txt"

# 仅在有 nikki 的固件上执行（镜像里没装代理时不做任何改动）
uci -q get nikki >/dev/null 2>&1 || {
	echo "Skip proxy network tuning: nikki not installed" >>"$LOGFILE"
	exit 0
}

# --- 1) 防火墙：软件 offloading 开、硬件关 ---
if uci -q get "firewall.@defaults[0]" >/dev/null 2>&1; then
	uci set firewall.@defaults[0].flow_offloading='1'
	uci set firewall.@defaults[0].flow_offloading_hw='0'
fi

# --- 2) 防火墙：拒绝 LAN 的 IPv6 出口（只拦转发，路由器自身 IPv6 到 VPS 不受影响）---
if ! uci -q show firewall | grep -q "name='Reject-LAN-IPv6-egress'"; then
	uci add firewall rule >/dev/null
	uci set firewall.@rule[-1].name='Reject-LAN-IPv6-egress'
	uci set firewall.@rule[-1].src='lan'
	uci set firewall.@rule[-1].dest='wan'
	uci set firewall.@rule[-1].family='ipv6'
	uci set firewall.@rule[-1].proto='all'
	uci set firewall.@rule[-1].target='REJECT'
fi

# --- 3) dnsmasq：去掉重复劫持 ---
for section in $(uci -q show dhcp | sed -n 's/^dhcp\.\([^.=]*\)=dnsmasq$/\1/p'); do
	uci set "dhcp.${section}.dns_redirect='0'"
done

# --- 4) nikki 重载行为 ---
if uci -q get "nikki.procd" >/dev/null 2>&1; then
	uci set nikki.procd.fast_reload='0'
	uci set nikki.procd.clear_connections_on_reload='1'
fi

# --- 5) LAN 纯 IPv4 ---
if uci -q get network.lan >/dev/null 2>&1; then
	uci -q delete network.lan.ip6assign
	uci set network.lan.delegate='0'
fi

for section in $(uci -q show dhcp | sed -n 's/^dhcp\.\([^.=]*\)=dhcp$/\1/p'); do
	if [ "$(uci -q get "dhcp.${section}.interface")" = "lan" ]; then
		uci set "dhcp.${section}.ra='disabled'"
		uci set "dhcp.${section}.dhcpv6='disabled'"
		uci set "dhcp.${section}.ndp='disabled'"
	fi
done

# --- 6) nikki：只代理 IPv4，但保留 IPv6 DNS 劫持 ---
if uci -q get nikki.proxy >/dev/null 2>&1; then
	uci set nikki.proxy.ipv6_proxy='0'
	uci set nikki.proxy.ipv6_dns_hijack='1'
fi

# --- 7) 清理历史遗留：GEOSITE,wechat / GEOSITE,tencent ---
#    这两个分类在 MetaCubeX 的 geosite.dat 里不存在，写了会导致
#    "configuration file test failed"、mihomo 根本起不来。
for sec in $(uci -q show nikki 2>/dev/null | sed -n "s/^nikki\.\(@rule\[[0-9]*\]\)\.type='GEOSITE'$/\1/p"); do
	matcher=$(uci -q get "nikki.${sec}.matcher")
	case "$matcher" in
		wechat|tencent)
			uci -q delete "nikki.${sec}"
			echo "Removed legacy rule GEOSITE,${matcher}" >>"$LOGFILE"
			;;
	esac
done

# --- 8) 清理历史遗留：mixin.yaml 里的 DNS 覆盖块（DNS 已收敛到订阅模板）---
if [ -f /etc/nikki/mixin.yaml ] && grep -q "network-tuning: dns profile" /etc/nikki/mixin.yaml; then
	sed -i '/^# network-tuning: dns profile$/,$d' /etc/nikki/mixin.yaml
	echo "Stripped legacy mixin DNS override" >>"$LOGFILE"
fi

uci commit network 2>/dev/null
uci commit firewall 2>/dev/null
uci commit dhcp 2>/dev/null
uci commit nikki 2>/dev/null

[ -x /sbin/fw4 ] && fw4 reload >/dev/null 2>&1

echo "Applied system network baseline: flow_offloading=1/hw=0, lan_pure_ipv4, reject_lan_ipv6, ipv6_proxy=0, ipv6_dns_hijack=1, dns_redirect=0, fast_reload=0" >>"$LOGFILE"

exit 0
