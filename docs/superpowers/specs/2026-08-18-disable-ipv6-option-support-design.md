# 设计规范：全平台固件构建支持禁止/关闭 IPv6 选项

## 1. 需求与背景
在当前的 ImmortalWrt ImageBuilder 项目中，`build-rockchip-25.12.x.yml` 和 `files/etc/uci-defaults/99-custom.sh` 已经支持了 `enable_ipv6` 选项（默认开启，可选关闭）。关闭 IPv6 时采用运行时 UCI/服务层配置：
- 保留固件内已有的 IPv6 相关软件包（避免包依赖冲突，且方便用户后续有需要时随时通过 WebUI 开启）；
- 首次开机时自动将 WAN6 置为 `none`、禁用 LAN RA 与 DHCPv6、关闭 `odhcpd` 服务、设置防火墙 `disable_ipv6='1'`。

本设计的目的在于将此特性全面扩展到所有固件构建工作流、所有构建脚本以及 GL.iNet 专用初始化脚本中，实现全平台统一的 IPv6 开关体验。

---

## 2. 总体架构与数据流

```
GitHub Actions UI (enable_ipv6: yes/no)
       │
       ▼ (Docker 环境变量 -e ENABLE_IPV6)
ImageBuilder 容器内 build*.sh
       │
       ▼ (生成配置文件 /etc/config/ipv6-settings)
写入固件文件系统 (files/etc/config/ipv6-settings)
       │
       ▼ (ImageBuilder 组装入固件 SquashFS)
固件首次开机启动
       │
       ▼ (运行 /etc/uci-defaults/99-custom.sh 或 glinet/99-custom.sh)
读取 /etc/config/ipv6-settings
       │
       ├─► enable_ipv6="yes" (默认): 保持原有 IPv6 配置
       │
       └─► enable_ipv6="no": 执行 UCI 与服务禁用逻辑
```

---

## 3. 具体修改范围与内容

### 3.1 GitHub Actions 工作流文件 (`.github/workflows/*.yml`)

在以下 12 个工作流中增加 `enable_ipv6` 输入选项，并传递给 Docker 容器：

1. `.github/workflows/build-x86-64-24.10.x.yml`
2. `.github/workflows/build-x86-64-25.12.x.yml`
3. `.github/workflows/build-rockchip-immortalWrt-24.10.x.yml`
4. `.github/workflows/build-wireless-router.yml`
5. `.github/workflows/build-wireless-router25.12.yml`
6. `.github/workflows/build-sunxi-cortexa53-24.10.x.yml`
7. `.github/workflows/build-sunxi-cortexa53-25.12.x.yml`
8. `.github/workflows/build-RaspBerryPi-24.10.x.yml`
9. `.github/workflows/build-QEMU-arm64-24.10.x.yml`
10. `.github/workflows/build-N1.yml`
11. `.github/workflows/build-iso.yml`
12. `.github/workflows/build-iso-25.12.x.yml`

**输入参数定义：**
```yaml
      enable_ipv6:
        description: |
          是否开启 IPv6 (WAN6 DHCPv6 / LAN RA / IPv6 防火墙)
        required: true
        default: 'yes'
        type: choice
        options:
          - 'yes'
          - 'no'
```

**Docker 启动环境变量传递：**
```yaml
        -e ENABLE_IPV6="${{ inputs.enable_ipv6 }}" \
```

---

### 3.2 构建脚本 (`*/build*.sh`)

在以下 11 个构建脚本中加入创建 `/home/build/immortalwrt/files/etc/config/ipv6-settings` 的逻辑：

1. `x86-64/build24.sh`
2. `x86-64/build25.sh`
3. `rockchip/build24.sh`
4. `mediatek-filogic/build23.sh`
5. `mediatek-filogic/build24.sh`
6. `mediatek-filogic/build25.sh`
7. `sunxi-cortexa53/build24.sh`
8. `sunxi-cortexa53/build25.sh`
9. `armsr-armv8/build.sh`
10. `raspberrypi/24.10/build.sh`
11. `n1/build.sh`

**写入逻辑：**
```bash
# 创建ipv6配置文件 yml传入环境变量ENABLE_IPV6 写入配置文件 供99-custom.sh读取
mkdir -p /home/build/immortalwrt/files/etc/config
cat << EOF > /home/build/immortalwrt/files/etc/config/ipv6-settings
enable_ipv6=${ENABLE_IPV6:-yes}
EOF
```

---

### 3.3 GL.iNet 首次开机脚本 (`glinet/99-custom.sh`)

在 `glinet/99-custom.sh` 中增加读取 `/etc/config/ipv6-settings` 并执行关闭逻辑：

```bash
# 检查配置文件ipv6-settings是否存在 该文件由build.sh动态生成
IPV6_SETTINGS_FILE="/etc/config/ipv6-settings"
enable_ipv6="yes"
if [ -f "$IPV6_SETTINGS_FILE" ]; then
    . "$IPV6_SETTINGS_FILE"
fi

# 是否关闭 IPv6 (由工作流 enable_ipv6 控制, 默认开启)
echo "enable_ipv6 value: $enable_ipv6" >>$LOGFILE
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
    echo "IPv6 已关闭 (WAN6=none, RA/DHCPv6 禁用, fw4 disable_ipv6=1)" >>$LOGFILE
else
    echo "IPv6 保持开启" >>$LOGFILE
fi
```

---

### 3.4 文档更新 (`README.md`)

在 `README.md` 中说明全平台构建工作流均已支持 `enable_ipv6` 选项及其工作原理。

---

## 4. 验证方案

1. **语法与格式检查**：
   - 验证所有 `.github/workflows/*.yml` 的 YAML 语法结构合法有效；
   - 验证所有 `build*.sh` 和 `glinet/99-custom.sh` 的 shell 语法正确（`sh -n` / `bash -n`）。
2. **一致性检查**：
   - 确认工作流中环境变量名与脚本接收变量名一致（`ENABLE_IPV6`）；
   - 确认写入的文件路径（`/etc/config/ipv6-settings`）与开机读取路径完全匹配。
