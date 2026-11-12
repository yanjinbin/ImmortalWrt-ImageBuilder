#!/bin/sh
# 透明代理(Nikki/TPROXY)场景下的网络稳定性修正
#
# 1) 关闭 flow offloading(软件/硬件): 流量卸载会绕过 netfilter, 使 TPROXY
#    时通时断 —— 表现为同一连接偶发失败、长连接变僵尸连接
# 2) 关闭 dnsmasq dns_redirect: 与 nikki 的 dport 53 -> :1053 劫持重复,
#    两套劫持叠加后 fake-ip 逻辑可能被打乱
# 3) dnsmasq min_cache_ttl=300: 默认/旧的 3600 会把 CDN 节点 IP 锁死一小时,
#    微信这类多 IP 的 CDN 容易出现解析与实际可用节点不一致
# 4) nikki fast_reload=0 + clear_connections_on_reload=1: 重载时彻底断开旧连接,
#    避免客户端抱着已失效的连接继续用(快速重载会保留旧连接状态)
#
# 幂等: 只写 uci; 末尾按需 reload, 失败也不影响重启后生效
LOGFILE="/etc/config/uci-defaults-log.txt"

# 仅在有 nikki 的固件上执行(镜像里没装代理时不做任何改动)
uci -q get nikki >/dev/null 2>&1 || {
	echo "Skip proxy network tuning: nikki not installed" >>"$LOGFILE"
	exit 0
}

if uci -q get "firewall.@defaults[0]" >/dev/null 2>&1; then
	uci set firewall.@defaults[0].flow_offloading='0'
	uci set firewall.@defaults[0].flow_offloading_hw='0'
fi

# dnsmasq 可能是单个匿名 section, 也可能有多个实例
for section in $(uci -q show dhcp | sed -n 's/^dhcp\.\([^.=]*\)=dnsmasq$/\1/p'); do
	uci set "dhcp.${section}.dns_redirect='0'"
	uci set "dhcp.${section}.min_cache_ttl='300'"
done

if uci -q get "nikki.procd" >/dev/null 2>&1; then
	uci set nikki.procd.fast_reload='0'
	uci set nikki.procd.clear_connections_on_reload='1'
fi

# 5) 重写 mihomo DNS 剖析: 去掉 fallback, 统一国内/国外 DoH 分流
#    - 订阅里的 fallback 用 DoT(tls://8.8.4.4、tls://1.1.1.1, 853), 走代理节点常失败,
#      实测 26 分钟失败 564 次, 每次失败都要等超时, 解析时快时慢
#    - fallback 的语义是"两套解析并发 + geoip 择一", 在"国内 + 代理"组合下纯属负担,
#      分流交给 nameserver-policy 更直接
#    - proxy-server-nameserver 去掉订阅里的第三方 DoH(实测 800ms, 国内 DoH 只要 140ms)
MIXIN_FILE="/etc/nikki/mixin.yaml"
if [ -f "$MIXIN_FILE" ] && ! grep -q "network-tuning: dns profile" "$MIXIN_FILE"; then
	cat >>"$MIXIN_FILE" <<'EOF'

# network-tuning: dns profile
dns:
  fallback: []
  default-nameserver:
    - 223.5.5.5
    - 119.29.29.29
  proxy-server-nameserver:
    - https://doh.pub/dns-query
    - https://dns.alidns.com/dns-query
  nameserver:
    - https://doh.pub/dns-query
    - https://dns.alidns.com/dns-query
  nameserver-policy:
    geosite:geolocation-!cn:
      - https://1.1.1.1/dns-query
      - https://8.8.8.8/dns-query
EOF
	uci set nikki.mixin.mixin_file_content='1'
fi

uci commit firewall 2>/dev/null
uci commit dhcp 2>/dev/null
uci commit nikki 2>/dev/null

# 首启防火墙已在运行; reload 让 flow_offloading=0 立即生效
[ -x /sbin/fw4 ] && fw4 reload >/dev/null 2>&1

echo "Applied proxy network tuning: flow_offloading=0, dns_redirect=0, min_cache_ttl=300, fast_reload=0" >>"$LOGFILE"

exit 0
