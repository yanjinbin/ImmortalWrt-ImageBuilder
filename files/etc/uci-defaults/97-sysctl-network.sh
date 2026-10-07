#!/bin/sh
# 内核网络优化 (sysctl): 仅 rockchip/armv8 系列 (R5C / E20C / R6S 等 ARM 软路由)
# 与人工调优参数一致: 16MB 收发缓冲 + MTU 探测 + conntrack + fastopen + BBR 拥塞控制
# BBR 依赖 kmod-tcp-bbr, 通过 /etc/modules.d 保证开机自动加载
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
# 收发缓冲
net.core.rmem_max=16777216
net.core.wmem_max=16777216
net.ipv4.tcp_rmem=4096 87380 16777216
net.ipv4.tcp_wmem=4096 65536 16777216
# TCP 吞吐/时延
net.ipv4.tcp_mtu_probing=1
net.ipv4.tcp_fastopen=3
net.ipv4.tcp_slow_start_after_idle=0
net.ipv4.tcp_max_syn_backlog=1024
net.ipv4.tcp_fin_timeout=15
net.ipv4.tcp_notsent_lowat=131072
# socket 缓冲 / 软中断积压 (缓解 RX drop)
net.core.netdev_max_backlog=2048
net.core.optmem_max=262144
net.ipv4.udp_rmem_min=8192
net.ipv4.udp_wmem_min=8192
net.ipv4.ip_local_port_range=10240 65535
# netfilter 连接跟踪 (4G 内存富余, 缩短空闲回收)
net.netfilter.nf_conntrack_max=131072
net.netfilter.nf_conntrack_tcp_timeout_established=3600
net.netfilter.nf_conntrack_tcp_timeout_time_wait=30
# 内存回收倾向 (无 swap, 避免无谓扫描)
vm.swappiness=10
# BBR 拥塞控制 (fq_codel qdisc 兼容; fq 未内建于该内核)
net.ipv4.tcp_congestion_control=bbr
# <<< codex network tuning <<<
EOF

# BBR: 加载 kmod-tcp-bbr 并固化开机加载 (模块由构建时 PACKAGES 引入)
if modprobe tcp_bbr 2>/dev/null; then
	mkdir -p /etc/modules.d
	echo tcp_bbr > /etc/modules.d/90-tcp-bbr
	echo "BBR 已启用并固化开机加载 (tcp_congestion_control=bbr)" >>"$LOGFILE"
else
	echo "警告: kmod-tcp-bbr 加载失败, 内核将回退默认拥塞控制" >>"$LOGFILE"
	# 模块不可用时移除 bbr 行, 避免 sysctl 报错
	sed -i "/^net.ipv4.tcp_congestion_control=bbr$/d" /etc/sysctl.conf
fi

sysctl -p /etc/sysctl.conf >/dev/null 2>&1
echo "Applied sysctl network tuning (target=$target)" >>"$LOGFILE"

exit 0
