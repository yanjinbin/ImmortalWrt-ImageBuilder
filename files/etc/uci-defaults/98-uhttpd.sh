#!/bin/sh
# uhttpd 性能与并发调优:
# 1. 提升并发脚本请求数 (max_requests = 30) - 解决 LuCI 多 ubus 并发及轮询排队阻塞卡顿
# 2. 提升最大连接数 (max_connections = 200)
# 3. 启用 HTTPS (443 端口) 监听 - 消除现代浏览器 (Chrome/Safari) HTTPS-First 探测时的 ~1s 回退超时延迟

if uci -q get uhttpd.main >/dev/null 2>&1; then
	uci set uhttpd.main.max_requests='30'
	uci set uhttpd.main.max_connections='200'
	uci -q del_list uhttpd.main.listen_https='0.0.0.0:443'
	uci -q del_list uhttpd.main.listen_https='[::]:443'
	uci add_list uhttpd.main.listen_https='0.0.0.0:443'
	uci add_list uhttpd.main.listen_https='[::]:443'
	uci commit uhttpd
fi

exit 0
