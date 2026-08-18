# 全平台固件构建支持禁止/关闭 IPv6 选项实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 ImmortalWrt-ImageBuilder 全平台编译工作流和构建脚本添加 `enable_ipv6` 选项支持，实现仅在开机配置层面禁用 IPv6（WAN6 置为 none、禁用 LAN RA/DHCPv6/odhcpd/防火墙 IPv6），完整保留 IPv6 软件包不卸载。

**Architecture:** GitHub Actions 工作流提供 `enable_ipv6` (yes/no) 选项，通过环境变量 `ENABLE_IPV6` 注入 ImageBuilder 容器，构建脚本在固件 `/etc/config/ipv6-settings` 写入配置，首次开机时由 `99-custom.sh`（通用与 GL.iNet）读取并应用关闭逻辑。

**Tech Stack:** GitHub Actions (YAML), Shell (POSIX sh / Bash), OpenWrt UCI & firewall4.

## Global Constraints

- **保留软件包**：不移除任何 IPv6 相关软件包（如 `odhcpd-ipv6only`, `luci-proto-ipv6` 等），仅通过 UCI 禁用协议与服务。
- **默认值一致**：所有工作流中 `enable_ipv6` 默认值必须为 `yes`。
- **变量命名统一**：工作流 input 名称 `enable_ipv6`，传递给 Docker 的环境变量 `ENABLE_IPV6`，写入文件的配置键 `enable_ipv6`。

---

### Task 1: 更新 GL.iNet 首次开机脚本 `glinet/99-custom.sh`

**Files:**
- Modify: `glinet/99-custom.sh:12-46`

- [ ] **Step 1: 在 `glinet/99-custom.sh` 中增加读取 `/etc/config/ipv6-settings`**

在 `glinet/99-custom.sh` 中读取 PPPoE 配置文件后，加入读取 `ipv6-settings` 的逻辑：
```sh
# 检查配置文件ipv6-settings是否存在 该文件由build.sh动态生成
IPV6_SETTINGS_FILE="/etc/config/ipv6-settings"
enable_ipv6="yes"
if [ -f "$IPV6_SETTINGS_FILE" ]; then
    . "$IPV6_SETTINGS_FILE"
fi
```

- [ ] **Step 2: 在 `glinet/99-custom.sh` 中增加 IPv6 关闭逻辑**

在 PPPoE 配置之后，增加关闭 IPv6 处理块：
```sh
# 是否关闭 IPv6 (由工作流 enable_ipv6 控制, 默认开启)
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
```

- [ ] **Step 3: 语法校验**

Run: `sh -n glinet/99-custom.sh`
Expected: 退出码 0，无语法错误。

- [ ] **Step 4: 提交**

```bash
git add glinet/99-custom.sh
git commit -m "feat(glinet): 在 99-custom.sh 中增加运行时禁用 IPv6 逻辑"
```

---

### Task 2: 更新各平台的固件构建脚本 `build*.sh`

**Files:**
- Modify: `x86-64/build24.sh:20-25`
- Modify: `x86-64/build25.sh:20-25`
- Modify: `rockchip/build24.sh:20-25`
- Modify: `mediatek-filogic/build23.sh:44-50`
- Modify: `mediatek-filogic/build24.sh:40-45`
- Modify: `mediatek-filogic/build25.sh:37-42`
- Modify: `sunxi-cortexa53/build24.sh:10-15`
- Modify: `sunxi-cortexa53/build25.sh:20-25`
- Modify: `armsr-armv8/build.sh:20-25`
- Modify: `raspberrypi/24.10/build.sh:10-15`
- Modify: `n1/build.sh:12-16`

- [ ] **Step 1: 在所有构建脚本中加入创建 `/home/build/immortalwrt/files/etc/config/ipv6-settings` 代码**

代码片段：
```bash
# 创建ipv6配置文件 yml传入环境变量ENABLE_IPV6 写入配置文件 供99-custom.sh读取
mkdir -p /home/build/immortalwrt/files/etc/config
cat << EOF > /home/build/immortalwrt/files/etc/config/ipv6-settings
enable_ipv6=${ENABLE_IPV6:-yes}
EOF
```

- [ ] **Step 2: 批量语法校验**

Run:
```bash
for f in x86-64/build24.sh x86-64/build25.sh rockchip/build24.sh mediatek-filogic/build23.sh mediatek-filogic/build24.sh mediatek-filogic/build25.sh sunxi-cortexa53/build24.sh sunxi-cortexa53/build25.sh armsr-armv8/build.sh raspberrypi/24.10/build.sh n1/build.sh; do
    bash -n "$f" || echo "Error in $f"
done
```
Expected: 全部通过，无语法错误。

- [ ] **Step 3: 提交**

```bash
git add x86-64/build24.sh x86-64/build25.sh rockchip/build24.sh mediatek-filogic/build23.sh mediatek-filogic/build24.sh mediatek-filogic/build25.sh sunxi-cortexa53/build24.sh sunxi-cortexa53/build25.sh armsr-armv8/build.sh raspberrypi/24.10/build.sh n1/build.sh
git commit -m "feat(scripts): 在所有 build*.sh 中增加写入 ipv6-settings 配置文件"
```

---

### Task 3: 更新 x86-64 与 Rockchip 24.10 工作流文件

**Files:**
- Modify: `.github/workflows/build-x86-64-24.10.x.yml`
- Modify: `.github/workflows/build-x86-64-25.12.x.yml`
- Modify: `.github/workflows/build-rockchip-immortalWrt-24.10.x.yml`

- [ ] **Step 1: 在工作流输入项增加 `enable_ipv6`**

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

- [ ] **Step 2: 在 Docker run 步骤中传递 `-e ENABLE_IPV6="${{ inputs.enable_ipv6 }}"`**

将 `-e ENABLE_IPV6="${{ inputs.enable_ipv6 }}" \` 加入各 docker run 参数中。

- [ ] **Step 3: 校验 YAML 语法**

Run: `python3 -c "import yaml; [yaml.safe_load(open(p)) for p in ['.github/workflows/build-x86-64-24.10.x.yml', '.github/workflows/build-x86-64-25.12.x.yml', '.github/workflows/build-rockchip-immortalWrt-24.10.x.yml']]"`
Expected: 退出码 0，无语法错误。

- [ ] **Step 4: 提交**

```bash
git add .github/workflows/build-x86-64-24.10.x.yml .github/workflows/build-x86-64-25.12.x.yml .github/workflows/build-rockchip-immortalWrt-24.10.x.yml
git commit -m "feat(workflow): 为 x86-64 与 Rockchip 24.10 工作流增加 enable_ipv6 选项"
```

---

### Task 4: 更新联发科无线路由与全志 sunxi 工作流文件

**Files:**
- Modify: `.github/workflows/build-wireless-router.yml`
- Modify: `.github/workflows/build-wireless-router25.12.yml`
- Modify: `.github/workflows/build-sunxi-cortexa53-24.10.x.yml`
- Modify: `.github/workflows/build-sunxi-cortexa53-25.12.x.yml`

- [ ] **Step 1: 在工作流输入项增加 `enable_ipv6`**

增加统一的 `enable_ipv6` choice 选项（默认 `yes`）。

- [ ] **Step 2: 在 Docker run 步骤中传递 `-e ENABLE_IPV6="${{ inputs.enable_ipv6 }}"`**

在联发科和全志各构建步骤的 docker run 命令中添加 `-e ENABLE_IPV6="${{ inputs.enable_ipv6 }}" \`。

- [ ] **Step 3: 校验 YAML 语法**

Run: `python3 -c "import yaml; [yaml.safe_load(open(p)) for p in ['.github/workflows/build-wireless-router.yml', '.github/workflows/build-wireless-router25.12.yml', '.github/workflows/build-sunxi-cortexa53-24.10.x.yml', '.github/workflows/build-sunxi-cortexa53-25.12.x.yml']]"`
Expected: 退出码 0，无语法错误。

- [ ] **Step 4: 提交**

```bash
git add .github/workflows/build-wireless-router.yml .github/workflows/build-wireless-router25.12.yml .github/workflows/build-sunxi-cortexa53-24.10.x.yml .github/workflows/build-sunxi-cortexa53-25.12.x.yml
git commit -m "feat(workflow): 为无线路由器与全志 sunxi 工作流增加 enable_ipv6 选项"
```

---

### Task 5: 更新树莓派、QEMU、N1 与 ISO 工作流文件

**Files:**
- Modify: `.github/workflows/build-RaspBerryPi-24.10.x.yml`
- Modify: `.github/workflows/build-QEMU-arm64-24.10.x.yml`
- Modify: `.github/workflows/build-N1.yml`
- Modify: `.github/workflows/build-iso.yml`
- Modify: `.github/workflows/build-iso-25.12.x.yml`

- [ ] **Step 1: 在工作流输入项增加 `enable_ipv6`**

增加统一的 `enable_ipv6` choice 选项（默认 `yes`）。

- [ ] **Step 2: 在 Docker run 步骤中传递 `-e ENABLE_IPV6="${{ inputs.enable_ipv6 }}"`**

在树莓派、QEMU、N1、ISO 的 docker run 命令中添加 `-e ENABLE_IPV6="${{ inputs.enable_ipv6 }}" \`。

- [ ] **Step 3: 校验 YAML 语法**

Run: `python3 -c "import yaml; [yaml.safe_load(open(p)) for p in ['.github/workflows/build-RaspBerryPi-24.10.x.yml', '.github/workflows/build-QEMU-arm64-24.10.x.yml', '.github/workflows/build-N1.yml', '.github/workflows/build-iso.yml', '.github/workflows/build-iso-25.12.x.yml']]"`
Expected: 退出码 0，无语法错误。

- [ ] **Step 4: 提交**

```bash
git add .github/workflows/build-RaspBerryPi-24.10.x.yml .github/workflows/build-QEMU-arm64-24.10.x.yml .github/workflows/build-N1.yml .github/workflows/build-iso.yml .github/workflows/build-iso-25.12.x.yml
git commit -m "feat(workflow): 为树莓派、QEMU、N1 与 ISO 工作流增加 enable_ipv6 选项"
```

---

### Task 6: 文档更新与全仓回归验证

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 `README.md` 说明**

在 `README.md` 中说明所有构建工作流均已支持 `enable_ipv6` 开关，说明其属于运行时配置关闭，保留软件包不卸载。

- [ ] **Step 2: 全仓工作流与 Shell 脚本完整回归校验**

编写并执行一次性回归脚本，扫描所有 `.github/workflows/*.yml` 的合法性以及所有 `build*.sh`、`99-custom.sh` 的语法有效性与 `ENABLE_IPV6` 引用完整性。

- [ ] **Step 3: 提交**

```bash
git add README.md
git commit -m "docs: 更新 README 关于全平台 IPv6 编译开关的说明"
```
