#!/bin/sh
# 默认主题由构建时写入的 /etc/luci-default-theme 决定 (工作流输入 default_theme)，
# 未指定时用 Vantage；主题包没装或模板不完整时按 vantage → footstrap → bootstrap 回退，
# 避免首启把 mediaurlbase 指到一个不存在的目录导致后台白屏。

DEFAULT_THEME_FILE="/etc/luci-default-theme"
THEME=""

[ -f "$DEFAULT_THEME_FILE" ] && THEME="$(cat "$DEFAULT_THEME_FILE" 2>/dev/null)"
[ -n "$THEME" ] || THEME="vantage"

theme_installed() {
    [ -d "/www/luci-static/$1" ] && [ -f "/usr/share/ucode/luci/template/themes/$1/header.ut" ]
}

SELECTED=""
for candidate in "$THEME" footstrap bootstrap; do
    if theme_installed "$candidate"; then
        SELECTED="$candidate"
        break
    fi
done

if [ -z "$SELECTED" ]; then
    echo "默认主题 $THEME 及其回退主题都不可用, 保持当前主题设置" >&2
    exit 0
fi

[ "$SELECTED" = "$THEME" ] || echo "默认主题 $THEME 不可用, 回退到 $SELECTED" >&2

uci -q get luci.main >/dev/null 2>&1 || uci set luci.main='core'
uci set luci.main.mediaurlbase="/luci-static/$SELECTED"
uci commit luci

exit 0
