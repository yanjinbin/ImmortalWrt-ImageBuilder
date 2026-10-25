#!/bin/sh
# 内核网络优化 (sysctl): 仅 rockchip/armv8 系列 (R5C / E20C / R6S 等 ARM 软路由)
# 参数与 2026-10 E20C 实测调优一致: 32MB 收发缓冲 + 软中断积压 + conntrack + RFS + BBR
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
# 软中断队列 / 收发批量 (缓解 RX backlog drop)
net.core.netdev_max_backlog=16384
net.core.netdev_budget=600
net.core.netdev_budget_usecs=8000
net.core.somaxconn=8192
net.core.optmem_max=262144
# RFS 流表 (需配合 network.globals.steering_flows)
net.core.rps_sock_flow_entries=32768
# 收发缓冲 (4G 内存富余, 上限 32MB)
net.core.rmem_max=33554432
net.core.wmem_max=33554432
net.ipv4.tcp_rmem=4096 131072 33554432
net.ipv4.tcp_wmem=4096 65536 33554432
net.ipv4.tcp_mem=65536 131072 262144
net.ipv4.udp_rmem_min=16384
net.ipv4.udp_wmem_min=16384
# TCP 吞吐/时延 (PPPoE MTU 1492, 代理长连接)
net.ipv4.tcp_mtu_probing=1
net.ipv4.tcp_fastopen=3
net.ipv4.tcp_slow_start_after_idle=0
net.ipv4.tcp_no_metrics_save=1
net.ipv4.tcp_autocorking=0
net.ipv4.tcp_max_syn_backlog=8192
net.ipv4.tcp_max_tw_buckets=65536
net.ipv4.tcp_fin_timeout=15
net.ipv4.tcp_tw_reuse=2
net.ipv4.tcp_keepalive_time=300
net.ipv4.tcp_keepalive_intvl=30
net.ipv4.tcp_keepalive_probes=5
net.ipv4.tcp_notsent_lowat=4194304
net.ipv4.ip_local_port_range=10240 65535
# 邻居表 (默认 128/512/1024 偏小)
net.ipv4.neigh.default.gc_thresh1=1024
net.ipv4.neigh.default.gc_thresh2=2048
net.ipv4.neigh.default.gc_thresh3=4096
# IPv4 分片重组 (默认仅 4MB)
net.ipv4.ipfrag_high_thresh=16777216
net.ipv4.ipfrag_low_thresh=12582912
net.ipv4.ipfrag_time=30
# netfilter 连接跟踪 (fullcone + UDP/QUIC 代理)
net.netfilter.nf_conntrack_max=131072
net.netfilter.nf_conntrack_tcp_timeout_established=7200
net.netfilter.nf_conntrack_tcp_timeout_time_wait=30
net.netfilter.nf_conntrack_udp_timeout=30
net.netfilter.nf_conntrack_udp_timeout_stream=120
# 内存回写 / 回收 (无 swap)
vm.swappiness=10
vm.min_free_kbytes=32768
vm.dirty_ratio=10
vm.dirty_background_ratio=5
vm.vfs_cache_pressure=50
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

# RFS: 为每个 RX 队列开启流表, 让代理连接落在处理它的核上, 减少跨核抖动
if uci -q get network.globals >/dev/null 2>&1; then
	uci set network.globals.steering_flows='16384'
	uci commit network
	[ -x /etc/init.d/packet_steering ] && /etc/init.d/packet_steering reload 2>/dev/null
	echo "RFS 流表已开启 (steering_flows=16384)" >>"$LOGFILE"
fi

sysctl -p /etc/sysctl.conf >/dev/null 2>&1
echo "Applied sysctl network tuning (target=$target)" >>"$LOGFILE"

exit 0
