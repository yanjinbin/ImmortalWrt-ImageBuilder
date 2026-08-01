#!/bin/sh
# 启用 collectd sensors 插件, 让统计页面显示 CPU/GPU 温度
# (与之前 R5C 上验证过的配置一致: sensors 区分 cpu-thermal / gpu-thermal)
if uci -q get luci_statistics.collectd_sensors >/dev/null 2>&1; then
	uci set luci_statistics.collectd_sensors.enable='1'
	uci commit luci_statistics
fi

exit 0
