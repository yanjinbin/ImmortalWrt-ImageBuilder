#!/bin/sh
# 默认主题设为 Footstrap (luci-theme-footstrap)
uci -q get luci.main >/dev/null 2>&1 || uci set luci.main='core'
uci set luci.main.mediaurlbase='/luci-static/footstrap'
uci commit luci

exit 0
