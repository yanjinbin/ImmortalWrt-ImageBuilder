#!/bin/sh
# 内核网络基线 (sysctl): 仅 rockchip/armv8 系列 (R5C / E20C / R6S 等 ARM 软路由)
# 只保留对「TPROXY + mihomo 本机中转」有明确作用的项, 其余一律用系统默认值:
#   - 收发缓冲上限: quic-go (hysteria2 / tuic) 需要 >= 7MB 的 UDP 缓冲, TCP 自动调优上限同步放宽
#   - tcp_mtu_probing: PPPoE (MTU 1492) 下的 PMTUD 黑洞兜底
#   - tcp_slow_start_after_idle=0: 代理长连接空闲后不重新慢启动
#   - netdev_max_backlog / RFS: 2.5G 突发时的软中断积压与多核分发
#   - BBR: 本机到代理节点的上行拥塞控制 (依赖 kmod-tcp-bbr, 经 /etc/modules.d 开机加载)
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

BLOCK_START="# >>> network baseline >>>"
BLOCK_END="# <<< network baseline <<<"

# 删除旧标记块 (含老固件写入的 codex 标记块), 防止重复堆叠
sed -i "/^${BLOCK_START}$/,/^${BLOCK_END}$/d" /etc/sysctl.conf
sed -i "/^# >>> codex network tuning >>>$/,/^# <<< codex network tuning <<<$/d" /etc/sysctl.conf

cat >> /etc/sysctl.conf <<'EOF'
# >>> network baseline >>>
# 收发缓冲上限 (quic-go 需要 >= 7MB UDP 缓冲; TCP 自动调优上限)
net.core.rmem_max=33554432
net.core.wmem_max=33554432
net.ipv4.tcp_rmem=4096 131072 33554432
net.ipv4.tcp_wmem=4096 65536 33554432
# PPPoE MTU 1492: PMTUD 黑洞兜底
net.ipv4.tcp_mtu_probing=1
# 代理长连接空闲后保持拥塞窗口
net.ipv4.tcp_slow_start_after_idle=0
# 软中断积压 / RFS 流表 (需配合 network.globals.steering_flows)
net.core.netdev_max_backlog=16384
net.core.rps_sock_flow_entries=32768
# BBR 拥塞控制 (fq_codel qdisc 兼容; fq 未内建于该内核)
net.ipv4.tcp_congestion_control=bbr
# 稳定性: 不带 loopback 的 TIME_WAIT 复用; TFO 仅客户端 (路由器不做服务端)
net.ipv4.tcp_tw_reuse=1
net.ipv4.tcp_fastopen=1
# 高并发 NAT + 代理连接表 (4GB 设备余量充足, 现场活跃连接 < 100)
net.netfilter.nf_conntrack_max=131072
net.netfilter.nf_conntrack_tcp_timeout_established=7200
net.netfilter.nf_conntrack_tcp_timeout_time_wait=30
net.netfilter.nf_conntrack_udp_timeout=30
net.netfilter.nf_conntrack_udp_timeout_stream=120
# 无 swap 设备
vm.swappiness=10
# <<< network baseline <<<
EOF

# 旧镜像把 conntrack / BBR 拆在 /etc/sysctl.d 里, 与上面的标记块形成两份来源,
# 改一处不生效; 统一收敛到标记块后删除这些文件 (幂等)
for legacy in /etc/sysctl.d/11-nf-conntrack.conf /etc/sysctl.d/12-tcp-bbr.conf; do
	if [ -f "$legacy" ]; then
		rm -f "$legacy"
		echo "Removed legacy $(basename "$legacy")" >>"$LOGFILE"
	fi
done

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

# RFS/RPS: 为每个 RX 队列开启流表并把软中断分发到多核 (代理连接落在处理它的核上, 减少跨核抖动)
if uci -q get network.globals >/dev/null 2>&1; then
	uci set network.globals.steering_flows='16384'
	uci set network.globals.packet_steering='1'
	uci commit network
	[ -x /etc/init.d/packet_steering ] && /etc/init.d/packet_steering reload 2>/dev/null
	echo "RPS/RFS 已开启 (packet_steering=1, steering_flows=16384)" >>"$LOGFILE"
fi

sysctl -p /etc/sysctl.conf >/dev/null 2>&1
echo "Applied sysctl network tuning (target=$target)" >>"$LOGFILE"

exit 0
