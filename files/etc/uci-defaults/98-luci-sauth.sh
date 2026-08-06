#!/bin/sh
# LuCI 登录时长参数 (默认 396 天):
#   luci.sauth.cookie_days = 396   (cookie 记住登录时长, 与 rpcd 会话无关)
#   luci.sauth.sessiontime = 604800 (rpcd 会话保持 7 天, 绝不设大)
uci -q get luci.sauth >/dev/null 2>&1 || uci set luci.sauth='sauth'
uci set luci.sauth.cookie_days='396'
uci set luci.sauth.sessiontime='604800'
uci commit luci

exit 0
