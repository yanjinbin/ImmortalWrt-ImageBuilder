#!/bin/sh
# 内核网络优化 (sysctl): 仅 rockchip/armv8 系列 (R5C / E20C / R6S 等 ARM 软路由)
# 与人工调优参数一致: 16MB 收发缓冲 + MTU 探测 + conntrack + fastopen
# 写入 /etc/sysctl.conf 并立即生效; 使用标记块整体替换, 幂等防堆叠
LOGFILE="/etc/config/uci-defaults-log.txt"

target=$(awk -F"'" '/^DISTRIB_TARGET=/{print $2}' /etc/openwrt_release 2>/dev/null)
case "$target" in
	rockchip/*) ;;
	*)
		echo "Skip sysctl network tuning: DISTRIB_TARGET=$target" >>"$LOGFILE"
		exit 0
		;;
esac

BLOCK_START="# >>> codex network tuning >>>"
BLOCK_END="# <<< codex network tuning <<<"

# 删除旧标记块, 防止重复堆叠
sed -i "/^${BLOCK_START}$/,/^${BLOCK_END}$/d" /etc/sysctl.conf

cat >> /etc/sysctl.conf <<'EOF'
# >>> codex network tuning >>>
net.core.rmem_max=16777216
net.core.wmem_max=16777216
net.ipv4.tcp_rmem=4096 87380 16777216
net.ipv4.tcp_wmem=4096 65536 16777216
net.ipv4.tcp_mtu_probing=1
net.netfilter.nf_conntrack_max=131072
net.ipv4.tcp_fastopen=3
# <<< codex network tuning <<<
EOF

sysctl -p /etc/sysctl.conf >/dev/null 2>&1
echo "Applied sysctl network tuning (target=$target)" >>"$LOGFILE"

exit 0
