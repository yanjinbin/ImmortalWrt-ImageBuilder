#!/bin/sh
# 预置 nikki: 开机启用 + 启动延迟, 并把构建期注入的默认订阅建成 uci 段。
#
# 默认订阅来源: workflow 的 secrets.NIKKI_SUBSCRIPTION_URL → 构建时写入
# /etc/nikki-subscription-url。令牌只留在设备 uci 里, 读入后立刻删除该文件。
# 未提供时只启用服务, 订阅刷机后再由运维脚本 (~/.ssh/r5c-optimized/deploy.sh)
# 或 LuCI 添加。
LOGFILE="/etc/config/uci-defaults-log.txt"

uci -q get nikki >/dev/null 2>&1 || exit 0

SUB_URL_FILE="/etc/nikki-subscription-url"
if [ -f "$SUB_URL_FILE" ]; then
	SUB_URL="$(tr -d '\r\n' <"$SUB_URL_FILE")"
	rm -f "$SUB_URL_FILE"

	if [ -n "$SUB_URL" ]; then
		# 复用已有的 oralcure 段 (keep-config 刷机时可能存在), 否则新建
		section=$(uci -q show nikki | sed -n "s/^nikki\.\([^.=]*\)\.name='oralcure'\$/\1/p" | head -1)
		if [ -z "$section" ]; then
			section=$(uci add nikki subscription)
		fi
		uci set "nikki.${section}=subscription"
		uci set "nikki.${section}.name=oralcure"
		uci set "nikki.${section}.url=$SUB_URL"
		uci set "nikki.${section}.user_agent=clash"
		uci set "nikki.${section}.prefer=remote"
		uci set "nikki.${section}.auto_update=1"
		uci set nikki.config.profile="subscription:${section}"
		echo "已预置 nikki 订阅 oralcure (profile=subscription:${section})" >>"$LOGFILE"
	fi
fi

uci set nikki.config.enabled='1'
# 首启留给 PPPoE 拨号的时间, 避免订阅拉取失败导致服务没起来 (失败了也不影响直连)
uci set nikki.config.start_delay='30'

# 没有预置订阅但设备上已有订阅段时, 选中第一个, 避免「服务起来了但没配置」
if [ -z "$(uci -q get nikki.config.profile)" ]; then
	first=$(uci -q show nikki | sed -n 's/^nikki\.\([^.=]*\)=subscription$/\1/p' | head -1)
	if [ -n "$first" ]; then
		uci set nikki.config.profile="subscription:$first"
		echo "nikki profile -> subscription:$first" >>"$LOGFILE"
	fi
fi

uci commit nikki
/etc/init.d/nikki enable >/dev/null 2>&1

echo "nikki 已设为开机启用" >>"$LOGFILE"

exit 0
