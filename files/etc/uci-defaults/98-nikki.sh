#!/bin/sh
# 预置 nikki: 订阅地址来自构建时写入的 /etc/nikki-subscription-url（工作流的
# secrets.NIKKI_SUBSCRIPTION_URL），并默认开机启用。
# 没带地址时只启用服务、不动订阅，避免把订阅写进公开仓库。
LOGFILE="/etc/config/uci-defaults-log.txt"

uci -q get nikki >/dev/null 2>&1 || exit 0

SUB_URL_FILE="/etc/nikki-subscription-url"
if [ -f "$SUB_URL_FILE" ]; then
	SUB_URL="$(cat "$SUB_URL_FILE" 2>/dev/null)"
	# 令牌只在 uci 里留一份，避免在 /etc 下多一份明文副本
	rm -f "$SUB_URL_FILE"

	if [ -n "$SUB_URL" ]; then
		uci set nikki.subscription=subscription 2>/dev/null || true
		uci set nikki.subscription.name='oralcure'
		uci set nikki.subscription.url="$SUB_URL"
		uci set nikki.subscription.user_agent='clash'
		uci set nikki.subscription.prefer='remote'
		uci set nikki.subscription.auto_update='1'
		echo "已预置 nikki 订阅地址" >>"$LOGFILE"
	fi
fi

uci set nikki.config.enabled='1'
# 首启留给 PPPoE 拨号的时间, 避免订阅拉取失败导致服务没起来 (失败了也不影响直连)
uci set nikki.config.start_delay='30'
uci commit nikki
/etc/init.d/nikki enable >/dev/null 2>&1

echo "nikki 已设为开机启用" >>"$LOGFILE"

exit 0
