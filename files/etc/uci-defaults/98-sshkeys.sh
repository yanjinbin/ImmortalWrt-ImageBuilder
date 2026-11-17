#!/bin/sh
# 预置 SSH 公钥 (root 用户, 对应 LuCI: 系统 -> 管理权 -> SSH-Keys)
#
# 构建时由 rockchip/build25.sh 根据 workflow 的 secrets.SSH_PUBKEY 生成:
#   /etc/dropbear/authorized_keys       直接可用的公钥 (镜像内已写入)
#   /etc/dropbear/authorized_keys.baked 同内容的备份, 用于 keep-config 刷机时恢复
#
# 首启做两件事:
#   1) 把预置公钥合并进 /etc/dropbear/authorized_keys, 保留用户在 LuCI 里手工加的其它公钥,
#      并去重 (sysupgrade 保留配置时固件自带文件会被旧配置覆盖, 这里补回来)
#   2) 修正权限: dropbear 要求 ~/.ssh 目录 0700、authorized_keys 0600 且属主 root,
#      否则公钥会被静默忽略 (只能退回密码登录)
LOGFILE="/etc/config/uci-defaults-log.txt"
DROPBEAR_DIR="/etc/dropbear"
KEY_FILE="/etc/dropbear/authorized_keys"
BAKED_FILE="/etc/dropbear/authorized_keys.baked"

[ -d "$DROPBEAR_DIR" ] || mkdir -p "$DROPBEAR_DIR"
chmod 700 "$DROPBEAR_DIR" 2>/dev/null

if [ -s "$BAKED_FILE" ]; then
	added=0
	[ -f "$KEY_FILE" ] || : > "$KEY_FILE"

	while IFS= read -r key || [ -n "$key" ]; do
		# 去掉 CRLF / 行尾空白, 跳过空行和注释
		key=$(printf '%s' "$key" | tr -d '\r')
		key=$(printf '%s' "$key" | sed 's/[[:space:]]*$//')
		[ -z "$key" ] && continue
		case "$key" in \#*) continue ;; esac

		if ! grep -qxF "$key" "$KEY_FILE" 2>/dev/null; then
			printf '%s\n' "$key" >> "$KEY_FILE"
			added=$((added + 1))
		fi
	done < "$BAKED_FILE"

	echo "已合并 $added 条预置 SSH 公钥到 $KEY_FILE" >>"$LOGFILE"
fi

if [ -f "$KEY_FILE" ]; then
	chmod 600 "$KEY_FILE" 2>/dev/null
	chown root:root "$KEY_FILE" 2>/dev/null
fi

# dropbear 默认开机自启; 这里兜底一次, 避免因其它脚本误关导致公钥不生效
[ -x /etc/init.d/dropbear ] && /etc/init.d/dropbear enable 2>/dev/null

exit 0
