#!/bin/sh
# LuCI 365 天免密登录参数:
#   luci.sauth.cookie_days = 365   (cookie 记住登录时长, 与 rpcd 会话无关)
#   luci.sauth.sessiontime = 604800 (rpcd 会话保持 7 天, 绝不设大)
uci -q get luci.sauth >/dev/null 2>&1 || uci set luci.sauth='sauth'
uci set luci.sauth.cookie_days='365'
uci set luci.sauth.sessiontime='604800'
uci commit luci

exit 0
