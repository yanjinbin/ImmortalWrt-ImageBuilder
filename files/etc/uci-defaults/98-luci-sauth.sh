#!/bin/sh
# LuCI 登录时长参数 (默认 396 天):
#   luci.sauth.cookie_days = 396   (cookie 记住登录时长, 与 rpcd 会话无关)
#   luci.sauth.sessiontime = 604800 (rpcd 会话保持 7 天, 绝不设大)
uci -q get luci.sauth >/dev/null 2>&1 || uci set luci.sauth='sauth'
# 只在没有配置时写入默认值，避免升级固件覆盖用户在 LuCI 中设置的天数。
uci -q get luci.sauth.cookie_days >/dev/null 2>&1 || uci set luci.sauth.cookie_days='396'
# rpcd 会话只保留 7 天；长期免密由 LuCI cookie 和浏览器 localStorage 提供。
uci set luci.sauth.sessiontime='604800'
uci commit luci

exit 0
