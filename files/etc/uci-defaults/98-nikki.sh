#!/bin/sh
# 预置 nikki: 只负责「开机启用 + 启动延迟」。
#
# 订阅地址不进镜像、不走 secret:
#   - 重刷后订阅由运维侧脚本写入 (r5c-optimized/deploy.sh 或 LuCI),
#     这样镜像里不会留下任何令牌, 也不会因为换了订阅还要重新构建。
#   - 若镜像里已经存在订阅段 (例如由 sysupgrade 保留的 /etc/config/nikki),
#     首启时把 profile 指向第一个订阅, 避免「服务起来了但没选中配置」。
LOGFILE="/etc/config/uci-defaults-log.txt"

uci -q get nikki >/dev/null 2>&1 || exit 0

uci set nikki.config.enabled='1'
# 首启留给 PPPoE 拨号的时间, 避免订阅拉取失败导致服务没起来 (失败了也不影响直连)
uci set nikki.config.start_delay='30'

if [ -z "$(uci -q get nikki.config.profile)" ]; then
	first=$(uci -q show nikki | sed -n 's/^nikki\.\([^.=]*\)=subscription$/\1/p' | head -1)
	if [ -n "$first" ]; then
		uci set nikki.config.profile="subscription:$first"
		echo "nikki profile -> subscription:$first" >>"$LOGFILE"
	fi
fi

uci commit nikki
/etc/init.d/nikki enable >/dev/null 2>&1

echo "nikki 已设为开机启用 (订阅需刷机后配置)" >>"$LOGFILE"

exit 0
