# [新手指导](https://github.com/wukongdaily/AutoBuildImmortalWrt/wiki) 👈🏻
# ImmortalWrt-ImageBuilder

**⚠️ 重要声明**

> **本项目为个人独立维护的第三方项目(脚本)，与 ImmortalWrt 官方没有关联。** <br>
> **项目中使用了 ImmortalWrt 官方 ImageBuilder 工具打包生成固件。<br>
> 但用户自行定制产生的任何 bug，均不代表 ImmortalWrt 官方固件的 bug**<br>
> **为了不给 ImmortalWrt 上游维护者增加额外负担和麻烦，所有相关问题请勿在 ImmortalWrt 群内反馈**。  <br>
> **建议各位在本项目 [Discussions](https://github.com/wukongdaily/ImmortalWrt-ImageBuilder/discussions) 中提问或讨论**


---

[![GitHub](https://img.shields.io/github/license/wukongdaily/AutoBuildImmortalWrt.svg?label=LICENSE&logo=github&logoColor=%20)](https://github.com/wukongdaily/AutoBuildImmortalWrt/blob/master/LICENSE)
![GitHub Stars](https://img.shields.io/github/stars/wukongdaily/AutoBuildImmortalWrt.svg?style=flat&logo=appveyor&label=Stars&logo=github)
![GitHub Forks](https://img.shields.io/github/forks/wukongdaily/AutoBuildImmortalWrt.svg?style=flat&logo=appveyor&label=Forks&logo=github)

## 🤔 这是什么？
基于 CI 的 ImageBuilder 工作流，用于自动化构建 ImmortalWrt 固件。
> 1、支持自定义固件大小 默认1GB 不建议设置过大 推荐1G-2G 更大需求可通过自定义插件里的扩容插件自行扩容<br>
> 2、支持可选预安装docker（可选）支持在UI上勾选是否集成商店 （24.10.6以下）<br>
> 3、支持按需增加[第三方软件](https://github.com/wukongdaily/store/blob/master/README.md)  如何集成 https://github.com/wukongdaily/AutoBuildImmortalWrt/discussions/209 <br>
> 4、点击这里查看👉🏻[全部支持的机型列表](https://github.com/wukongdaily/AutoBuildImmortalWrt/blob/master/SUPPORT.md) 👈🏻<br>
> 5、在UI上 新增luci版本的可选项，默认最新版25.12.x https://github.com/wukongdaily/AutoBuildImmortalWrt/discussions/426<br>
> 6、支持设置管理地址的ip 比如192.168.100.1 这里强调 这项功能仅针对多网口机型 单网口的逻辑还是自动获取ip模式（dhcp）无固定ip<br>
> 7、对于[插件追新的用户 建议前往run项目 下载run后 ](https://github.com/wukongdaily/RunFilesBuilder/discussions/41)用命令sh xx.run 覆盖安装 <br>
> 8、支持24.10.x 、25.12.x 等版本 （包括x86-64-ISO、x86-64、rockchip、全志sunxi、无线路由器）

## 🧩 本仓库定制内容

> 当前只维护 **rockchip 25.12.x APK 安装方式**（24.10 及以下版本不做支持）。

**默认支持机型**：FriendlyARM NanoPi R5C、Radxa E20C（工作流 `Build 25.12.x Rockchip` 中可选，默认 R5C）。

**E20C 网口指示灯**：首启自动为 RTL8168H/8111H WAN RJ45 网口配置 10/100/1000M 链路和 RX/TX 活动指示，不影响机身 WAN/LAN 指示灯。

**已集成插件/主题**：
- 代理：nikki + luci-app-nikki（来源：`yanjinbin/OpenWrt-nikki` fork 的 prebuilt release，构建时可选 latest 或指定 release tag，含魔改内容）+ mihomo（不编译，工作流直接从 [MetaCubeX/mihomo releases](https://github.com/MetaCubeX/mihomo/releases) 下载所选版本/平台的预编译二进制写入固件）
- 主题：luci-theme-openwrt（默认，官方仓库）、luci-theme-uniwrt（`yanjinbin/uniwrt-luci`）、luci-theme-footstrap（`yanjinbin/luci-theme-footstrap`）；已移除 argon
- 默认主机名：ImmortalWrt-<软路由型号>-Gateway（如 E20C → `ImmortalWrt-E20C-Gateway`、NanoPi-R5C → `ImmortalWrt-NanoPi-R5C-Gateway`），首启按板型自动设置
- 默认登录密码：`666666`（LuCI 系统->管理权 可修改）
- LuCI 登录时长：默认 396 天（`luci.sauth.cookie_days=396`，rpcd `sessiontime` 固定 604800 不放大；cookie + localStorage 双保险，覆盖通用/OpenWrt/uniwrt/footstrap/bootstrap 主题；密码页"登录时长（天）/ Login duration (days)"支持中英文显示）
- 默认主题：Footstrap（`luci.main.mediaurlbase=/luci-static/footstrap`）
- 流量统计：luci-app-statistics + luci-i18n-statistics-zh-cn（官方仓库），默认预装 collectd 常用模块：CPU / 内存 / 负载 / 接口流量 / 磁盘 / 传感器温度（CPU/GPU 温度，自动带 lm-sensors），首启自动启用
- 流量监控：luci-app-bandix（基础版）+ luci-app-bandix-plus（多接口版）；Plus 后端、前端和中文包均使用 timsaya 官方 Release APK 并校验 SHA-256
- 分区扩容：luci-app-partexp（sirpdboy，wukongdaily/apk 源）

**默认 LAN 口 IP**：工作流 UI 中 `custom_router_ip` 已改为下拉选择（默认 `192.168.1.1`，可选 `192.168.100.1` 等），仅对多网口机型生效。

**mihomo 版本/平台**：工作流 UI 支持选择或填写 mihomo 版本（默认 `1.19.27`，可选 `latest` 最新版或自定义版本号）和平台（默认 `arm64`，覆盖 R5C / R6S / E20C；可选 `amd64`、`armv7` 等或自定义）。

构建完成后固件自动发布到**独立 Release 页面**（每次构建单独 tag：`Autobuild-<run>`），说明内容按本次构建参数（设备 / LAN IP / mihomo 版本 / 固件空间等）动态生成，可直接下载 `*.img.gz`。

## [基本用法步骤](https://github.com/wukongdaily/AutoBuildImmortalWrt/wiki) 👈🏻
1、fork本项目<br>
2、在fork后的项目中 点击【action】 找到需要的工作流后 run-workflow<br>

## 虚拟机建议用哪条工作流？下图↓
<img width="30%" height="30%" alt="image" src="https://github.com/user-attachments/assets/743027e0-584a-4842-bfb3-0dff22de9101" /> <br>
虚拟机用户建议直接构建ISO镜像 此过程分2个阶段 阶段一构建固件imm 阶段二将其封装iso格式的安装器 总计耗时大约7-8分钟  <br>
ISO在虚拟机引导后 跑码结束后，在命令行输入 `ddd` 按提示 完成虚拟磁盘的写入（安装immortalwrt到虚拟磁盘）<br>
这样做也比较灵活 避免了格式转换和解压 同时还可以指定安装某个磁盘 而安装后的磁盘剩余空间也能加以利用。<br>
详细的解说 可以参考我的另一个项目 [img-installer](https://github.com/wukongdaily/armbian-installer) 

## 虚拟机用户使用的教学⬇️ ISO 
[![操作步骤](https://img.shields.io/badge/YouTube-123456?logo=youtube&labelColor=ff0000)](https://www.youtube.com/watch?v=ftSE3wSJi64) [![Bilibili](https://img.shields.io/badge/Bilibili-123456?logo=bilibili&logoColor=fff&labelColor=fb7299)](https://www.bilibili.com/video/BV1enxMzwEUe/) <br>
【绿联NAS安装immortalwrt25.12】https://www.bilibili.com/video/BV1AyZcBsErt/

## 物理机如何使用ISO格式的安装器(本项目独有)
- Windows 建议将ISO拷贝到制作好的[Ventoy](https://www.ventoy.net/cn/index.html)<br>
  <img width="303" height="90" alt="image" src="https://github.com/user-attachments/assets/34d73e24-3100-4c0d-a904-5f114d867793" />

- macOS 使用[balenaEtcher](https://etcher.balena.io/) 将ISO 刻录到U盘即可<br>
  <img width="285" height="188" alt="image" src="https://github.com/user-attachments/assets/cd09be82-2670-404c-8878-c2782b3c8374" />

- 将制作好的U盘提前插在软路由 然后启动后 按Del 或者F12、F11、F7等 使U盘成为第一启动盘

  <img width="50%" alt="image" src="https://github.com/user-attachments/assets/a1ba38d9-305c-41dd-8441-9e61c3dcae1d" /> <br>
- 启动后在命令行输入 ddd 按提示 完成硬盘的写入 硬盘剩余空间你还可以自动分配<br>
- ISO安装器原理 点这里查看 https://github.com/wukongdaily/img-installer
- [视频教学参考 精准空降到 13:46 ](https://www.bilibili.com/video/BV1DQXVYFENr/?share_source=copy_web&vd_source=0bb92241fb28a55c32c2e5132116b594&t=826)
- 这是一个值得推广的方法 真心希望你能吸收、学会 费了很大心思的。没错、从今往后 [任何OpenWrt都有安装器了](https://github.com/wukongdaily/img-installer)

## 如何查询imm仓库内有哪些插件
https://mirrors.sjtug.sjtu.edu.cn/immortalwrt/releases/24.10.4/packages/x86_64/luci/
## 如何查询imm仓库外目前可以集成哪些插件
https://github.com/wukongdaily/store
> 具体方法 https://github.com/wukongdaily/AutoBuildImmortalWrt/discussions/209
## 【视频教程】如何集成第三方插件？
https://www.youtube.com/watch?v=KN6AJYV1hBI <br>
https://www.youtube.com/watch?v=7i6BQeitUtE

## 旁路由的用户必读
近期不少用户修改配置文件中的默认ip地址，误认为这个工作流可以直接设置旁路ip。这是巨大的误解，这样设置就乱套了。<br>
旁路的逻辑应该是单网口模式。根据下面的固件属性可知。单网口默认采取`dhcp模式`，用户应当自行在上一级路由器查看给imm路由器分配的ip地址。
然后通过该ip来访问imm后台页面，在imm后台页面中，根据自己主路由的网段 自行配置旁路的ip地址。

## 正常路由模式必读
所谓正常的路由模式 就是指多网口用户，多网口的意思就是2个或者2个以上网口的情况。<br>
一般wan用于拨号或者自动获取ip <br>
而其他lan一般是给其他设备分配dhcp<br>
这种情况下 你可以修改路由器的默认ip  `192.168.100.1` 比如你可以修改为`192.168.80.1 ` 诸如此类。<br>
没错，修改此ip 无非就是为了避免跟光猫或者跟家庭中的其他路由器网段冲突。大多数用户，无需更改。

## 该固件默认属性？(必读)
- 该固件刷入【单网口设备】默认采用DHCP模式,自动获得ip。类似NAS的做法
- 该固件刷入【多网口设备】默认WAN口采用DHCP模式，LAN 口ip为  `192.168.100.1` <br>其中eth0为WAN 其余网口均为LAN
- 若用户在工作流中勾选了拨号信息 则WAN口模式为pppoe拨号模式。
- 建议拨号用户使用之前重启一次光猫。
- 综合上述特点，【单网口设备】应该先接路由器，先在上级路由器查看一下它的ip 再访问。
- 上述特点 你都可以通过 `99-custom.sh` 配置和调整

## 特别说明
本项目构建的固件 为了易用性 wan口防火墙规则入站 是开启的，待首次调试完毕后，建议自行关闭。操作方法如下
网络——防火墙—— wan 的入站 选择拒绝 然后保存并应用即可。更多讨论[ 请参考这个话题](https://github.com/wukongdaily/AutoBuildImmortalWrt/discussions/341)
<img width="3860" height="870" alt="image" src="https://github.com/user-attachments/assets/d826bccd-f0df-4d4a-877d-b711b81fcf1a" />
同时此项设置的相关代码详见 `files/etc/uci-defaults/99-custom.sh` 行首

## ❤️其它GitHub Action项目推荐🌟 （建议收藏）⬇️
- ### [一键生成run插件] 🆕
- https://github.com/wukongdaily/RunFilesBuilder<br>
- ### [一键生成docker离线镜像] 🆕
- https://github.com/wukongdaily/DockerTarBuilder<br>
- ### [OpenWrt/Armbian IMG安装器ISO] 🆕
- https://github.com/wukongdaily/img-installer


## ❤️如何构建docker版ImmortalWrt（建议收藏）⬇️
https://wkdaily.cpolar.cn/15
# 🎉鸣谢

感谢以下项目与作者对本项目的贡献与灵感 ❤️

<div align="left">

<a href="https://github.com/immortalwrt"><img src="https://avatars.githubusercontent.com/immortalwrt?v=4&s=80" width="80" height="80" alt="immortalwrt" /></a>
<a href="https://github.com/Openwrt-Passwall"><img src="https://avatars.githubusercontent.com/Openwrt-Passwall?v=4&s=80" width="80" height="80" alt="Openwrt-Passwall" /></a>
<a href="https://github.com/sirpdboy"><img src="https://avatars.githubusercontent.com/sirpdboy?v=4&s=80" width="80" height="80" alt="sirpdboy" /></a>
<a href="https://github.com/ophub"><img src="https://avatars.githubusercontent.com/ophub?v=4&s=80" width="80" height="80" alt="ophub" /></a>
<a href="https://github.com/linkease"><img src="https://avatars.githubusercontent.com/linkease?v=4&s=80" width="80" height="80" alt="linkease" /></a>

<a href="https://github.com/coolsnowwolf"><img src="https://avatars.githubusercontent.com/coolsnowwolf?v=4&s=80" width="80" height="80" alt="coolsnowwolf" /></a>
<a href="https://github.com/stackia"><img src="https://avatars.githubusercontent.com/stackia?v=4&s=80" width="80" height="80" alt="stackia" /></a>
<a href="https://github.com/kiddin9"><img src="https://avatars.githubusercontent.com/kiddin9?v=4&s=80" width="80" height="80" alt="kiddin9" /></a>
<a href="https://github.com/sbwml"><img src="https://avatars.githubusercontent.com/sbwml?v=4&s=80" width="80" height="80" alt="sbwml" /></a>
<a href="https://github.com/kenzok8"><img src="https://avatars.githubusercontent.com/kenzok8?v=4&s=80" width="80" height="80" alt="kenzok8" /></a>

<a href="https://github.com/timsaya"><img src="https://avatars.githubusercontent.com/timsaya?v=4&s=80" width="80" height="80" alt="timsaya" /></a>
<a href="https://github.com/AdguardTeam"><img src="https://avatars.githubusercontent.com/AdguardTeam?v=4&s=80" width="80" height="80" alt="AdguardTeam" /></a>
<a href="https://github.com/Thaolga"><img src="https://avatars.githubusercontent.com/Thaolga?v=4&s=80" width="80" height="80" alt="Thaolga" /></a>
<a href="https://github.com/eamonxg"><img src="https://avatars.githubusercontent.com/eamonxg?v=4&s=80" width="80" height="80" alt="eamonxg" /></a>
<a href="https://github.com/nikkinikki-org"><img src="https://avatars.githubusercontent.com/nikkinikki-org?v=4&s=80" width="80" height="80" alt="nikkinikki-org" /></a>

<a href="https://github.com/gdy666"><img src="https://avatars.githubusercontent.com/gdy666?v=4&s=80" width="80" height="80" alt="gdy666" /></a>
<a href="https://github.com/lwb1978"><img src="https://avatars.githubusercontent.com/lwb1978?v=4&s=80" width="80" height="80" alt="lwb1978" /></a>
<a href="https://github.com/Tokisaki-Galaxy"><img src="https://avatars.githubusercontent.com/Tokisaki-Galaxy?v=4&s=80" width="80" height="80" alt="Tokisaki-Galaxy" /></a>
<a href="https://github.com/QiuSimons"><img src="https://avatars.githubusercontent.com/QiuSimons?v=4&s=80" width="80" height="80" alt="QiuSimons" /></a>
<a href="https://xz.vumstar.com/"><img src="https://xz.vumstar.com/static/img/logo.png" width="80" height="80" alt="wukongdaily" /></a>

</div>

## ❤️赞助作者 ⬇️⬇️

<a href="https://wkdaily.cpolar.top/01" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"
       alt="Buy Me A Coffee"
       style="width:15%; height:auto;">
</a>
