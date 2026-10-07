#!/bin/sh
# rockchip/armv8 软路由系统级默认优化 (R5C / E20C / R6S 等)
# 1) CPU governor -> performance: 降低转发抖动与时延 (R5C 温裕充足)
# 2) 无无线网卡的机型: 关闭空转的 wpad (hostapd/wpa_supplicant) 与 radius 服务
LOGFILE="/etc/config/uci-defaults-log.txt"

target=$(awk -F"'" '/^DISTRIB_TARGET=/{print $2}' /etc/openwrt_release 2>/dev/null)
case "$target" in
	rockchip/*) ;;
	*)
		echo "Skip rockchip system tuning: DISTRIB_TARGET=$target" >>"$LOGFILE"
		exit 0
		;;
esac

# 1) CPU governor -> performance (经 uci 固化, 重启后由 cpufreq 服务应用)
if [ -e /etc/config/cpufreq ]; then
	uci set cpufreq.cpufreq.governor0='performance'
	uci commit cpufreq
	for gov in /sys/devices/system/cpu/cpufreq/policy*/scaling_governor; do
		[ -w "$gov" ] && echo performance >"$gov"
	done
	echo "CPU governor 已设为 performance" >>"$LOGFILE"
fi

# 2) 无 ieee80211 无线网卡时, 关闭 wpad / radius (纯多余进程)
if [ -z "$(ls -A /sys/class/ieee80211/ 2>/dev/null)" ]; then
	[ -x /etc/init.d/wpad ] && { /etc/init.d/wpad stop 2>/dev/null; /etc/init.d/wpad disable 2>/dev/null; }
	[ -x /etc/init.d/radius ] && /etc/init.d/radius disable 2>/dev/null
	echo "未检测到无线网卡, 已关闭 wpad/radius" >>"$LOGFILE"
else
	echo "检测到无线网卡, 保留 wpad/radius" >>"$LOGFILE"
fi

exit 0
