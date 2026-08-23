#!/bin/sh
# 该脚本为immortalwrt首次启动时 运行的脚本 即 /etc/uci-defaults/99-custom.sh 也就是说该文件在路由器内 重启后消失 只运行一次
# 设置默认防火墙规则，方便虚拟机首次访问 WebUI
LOGFILE="/etc/config/uci-defaults-log.txt"
uci set firewall.@zone[1].input='ACCEPT'

# 设置主机名映射，解决安卓原生 TV 无法联网的问题
uci add dhcp domain
uci set "dhcp.@domain[-1].name=time.android.com"
uci set "dhcp.@domain[-1].ip=203.107.6.88"

# 检查配置文件是否存在
SETTINGS_FILE="/etc/config/pppoe-settings"
if [ ! -f "$SETTINGS_FILE" ]; then
    echo "PPPoE settings file not found. Skipping." >> $LOGFILE
else
   # 读取pppoe信息(由build.sh写入)
   . "$SETTINGS_FILE"
fi

# 检查配置文件ipv6-settings是否存在 该文件由build.sh动态生成
IPV6_SETTINGS_FILE="/etc/config/ipv6-settings"
enable_ipv6="no"
if [ -f "$IPV6_SETTINGS_FILE" ]; then
    . "$IPV6_SETTINGS_FILE"
fi

# 设置子网掩码 
uci set network.lan.netmask='255.255.255.0'
# 设置路由器管理后台地址
IP_VALUE_FILE="/etc/config/custom_router_ip.txt"
if [ -f "$IP_VALUE_FILE" ]; then
    CUSTOM_IP=$(cat "$IP_VALUE_FILE")
    # 设置路由器的管理后台地址
    uci set network.lan.ipaddr=$CUSTOM_IP
    echo "custom router ip is $CUSTOM_IP" >> $LOGFILE
fi


# 判断是否启用 PPPoE
echo "print enable_pppoe value=== $enable_pppoe" >> $LOGFILE
if [ "$enable_pppoe" = "yes" ]; then
    echo "PPPoE is enabled at $(date)" >> $LOGFILE
    # 设置拨号信息
    uci set network.wan.proto='pppoe'                
    uci set network.wan.username=$pppoe_account     
    uci set network.wan.password=$pppoe_password     
    uci set network.wan.peerdns='1'                  
    uci set network.wan.auto='1' 
    echo "PPPoE configuration completed successfully." >> $LOGFILE
else
    echo "PPPoE is not enabled. Skipping configuration." >> $LOGFILE
fi

# 是否关闭 IPv6 (由工作流 enable_ipv6 控制, 默认关闭)
echo "enable_ipv6 value: $enable_ipv6" >> $LOGFILE
if [ "$enable_ipv6" = "no" ]; then
    # 关闭 WAN6 / LAN6 接口
    if uci -q get network.wan6 >/dev/null; then
        uci set network.wan6.proto='none'
    fi
    uci -q delete network.lan6
    uci -q delete network.lan.ip6assign
    uci -q delete network.lan.ip6hint
    uci -q delete network.lan.ip6ifaceid
    uci -q delete network.lan.ip6class
    # 关闭 LAN 的 IPv6 RA/DHCPv6 (odhcpd)
    if uci -q get dhcp.lan >/dev/null; then
        uci set dhcp.lan.ra='disabled'
        uci set dhcp.lan.dhcpv6='disabled'
        uci -q delete dhcp.lan.ra_management
        uci -q delete dhcp.lan.ndp
        uci -q delete dhcp.lan.ra_slaac
    fi
    # 禁用 odhcpd 服务 (若存在)
    if [ -x /etc/init.d/odhcpd ]; then
        /etc/init.d/odhcpd disable
    fi
    # 防火墙关闭 IPv6 处理
    if uci -q get firewall.@defaults[0] >/dev/null; then
        uci set firewall.@defaults[0].disable_ipv6='1'
    fi
    uci commit network
    uci commit dhcp
    uci commit firewall
    echo "IPv6 已关闭 (WAN6=none, RA/DHCPv6 禁用, fw4 disable_ipv6=1)" >> $LOGFILE
else
    echo "IPv6 保持开启" >> $LOGFILE
fi

# 若安装了dockerd 则设置docker的防火墙规则
# 扩大docker涵盖的子网范围 '172.16.0.0/12'
# 方便各类docker容器的端口顺利通过防火墙 
if command -v dockerd >/dev/null 2>&1; then
    echo "检测到 Docker，正在配置防火墙规则..."
    FW_FILE="/etc/config/firewall"

    # 删除所有名为 docker 的 zone
    uci delete firewall.docker

    # 先获取所有 forwarding 索引，倒序排列删除
    for idx in $(uci show firewall | grep "=forwarding" | cut -d[ -f2 | cut -d] -f1 | sort -rn); do
        src=$(uci get firewall.@forwarding[$idx].src 2>/dev/null)
        dest=$(uci get firewall.@forwarding[$idx].dest 2>/dev/null)
        echo "Checking forwarding index $idx: src=$src dest=$dest"
        if [ "$src" = "docker" ] || [ "$dest" = "docker" ]; then
            echo "Deleting forwarding @forwarding[$idx]"
            uci delete firewall.@forwarding[$idx]
        fi
    done
    # 提交删除
    uci commit firewall
    # 追加新的 zone + forwarding 配置
    cat <<EOF >>"$FW_FILE"

config zone 'docker'
  option input 'ACCEPT'
  option output 'ACCEPT'
  option forward 'ACCEPT'
  option name 'docker'
  list subnet '172.16.0.0/12'

config forwarding
  option src 'docker'
  option dest 'lan'

config forwarding
  option src 'docker'
  option dest 'wan'

config forwarding
  option src 'lan'
  option dest 'docker'
EOF

else
    echo "未检测到 Docker，跳过防火墙配置。"
fi

# 设置所有网口可访问网页终端
uci delete ttyd.@ttyd[0].interface

# 设置所有网口可连接 SSH
uci set dropbear.@dropbear[0].Interface=''
uci commit

# 设置编译作者信息
FILE_PATH="/etc/openwrt_release"
NEW_DESCRIPTION="Packaged by wukongdaily"
sed -i "s/DISTRIB_DESCRIPTION='[^']*'/DISTRIB_DESCRIPTION='$NEW_DESCRIPTION'/" "$FILE_PATH"
# uhttpd 性能与并发优化 (提升并发请求数、连接数、开启 HTTPS 监听)
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
