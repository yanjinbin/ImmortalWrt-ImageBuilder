#!/bin/sh
# 首次启动: 立即刷新 LuCI 静态资源缓存键, 并启用开机检查 (覆盖 sysupgrade 保留配置场景)
rev="$(awk -F"'" '/DISTRIB_REVISION/{print $2}' /etc/openwrt_release 2>/dev/null)"
touch /lib/apk/db/installed 2>/dev/null || touch /usr/lib/opkg/status 2>/dev/null
[ -n "$rev" ] && echo "$rev" > /etc/fw-revision
/etc/init.d/fw-cache-bust enable
exit 0
