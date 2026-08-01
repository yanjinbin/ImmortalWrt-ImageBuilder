#!/bin/sh
# 启用 collectd 常用统计插件: CPU / 内存 / 负载 / 接口流量 / 磁盘 / 传感器温度
# (sensors 区分 cpu-thermal / gpu-thermal, 与之前 R5C 验证过的配置一致)
for plugin in cpu memory load interface df sensors; do
	if uci -q get "luci_statistics.collectd_${plugin}" >/dev/null 2>&1; then
		uci set "luci_statistics.collectd_${plugin}.enable"='1'
	fi
done
uci commit luci_statistics

exit 0
