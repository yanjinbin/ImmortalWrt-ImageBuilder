#!/bin/sh
# 默认主题设为 OpenWrt (luci-theme-openwrt)
uci -q get luci.main >/dev/null 2>&1 || uci set luci.main='core'
uci set luci.main.mediaurlbase='/luci-static/openwrt'
uci commit luci

exit 0
