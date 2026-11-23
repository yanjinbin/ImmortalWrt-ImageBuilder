# Rockchip 网络基线（TPROXY + PPPoE，稳定优先）

适用于 `rockchip/armv8`（NanoPi R5C / E20C / R6S 等）。固件只写**系统层**，分流规则、策略组、节点、DNS 全部来自 aliyun 订阅模板。

## 1. 目标与分层

```
光猫桥接 ── PPPoE ── 路由器
                       ├─ nikki/mihomo（TPROXY tcp+udp）：接管全屋 IPv4 + 路由器自身
                       ├─ LAN 纯 IPv4：RA/NDP 关闭 + v6 出口 REJECT
                       └─ WAN IPv6：仅供路由器自身连接 IPv6 节点
```

| 层 | 归属 | 内容 |
|---|---|---|
| 系统层 | 本仓库 `files/etc/uci-defaults/` | sysctl、防火墙 offload、LAN v6 策略、nikki 启停、qdisc |
| 策略层 | aliyun `template.yaml` | 规则、代理组、节点、DNS（fake-ip / DoH / 分流） |
| 订阅 | 刷机后写入 | 不进镜像、不走 secret，令牌只存在设备 uci 里 |

## 2. 固件写入的项

| 文件 | 作用 |
|---|---|
| `97-sysctl-network.sh` | sysctl 标记块：收发缓冲 32 MB、`tcp_mtu_probing`、`slow_start_after_idle=0`、backlog/RFS、BBR、`tcp_tw_reuse=1`、`tcp_fastopen=1`、`nf_conntrack_max=131072` + 超时、`vm.swappiness=10`；并删除旧镜像遗留的 `/etc/sysctl.d/11-nf-conntrack.conf`、`12-tcp-bbr.conf`，保证只有一个来源 |
| `98-nikki.sh` | 开机启用 nikki + `start_delay=30`；若有订阅段则选中第一个 profile；**不写任何订阅地址** |
| `99-network-tuning.sh` | `flow_offloading=0` / `_hw=0`；LAN 纯 IPv4（`delegate=0`、删 `ip6assign`、`ra/dhcpv6/ndp=disabled`）；`Reject-LAN-IPv6-egress`；`dns_redirect=0`、`min_cache_ttl=300`；`ipv6_proxy=0` + `ipv6_dns_hijack=1`；`fast_reload=0`、`clear_connections_on_reload=1`；nikki 日志清理 `*/30`、5 MB |
| `files/etc/hotplug.d/iface/99-qdisc` | PPPoE `ifup` 后给 `pppoe-wan` 挂 `fq_codel`（重拨自动重挂） |

## 3. 稳定优先的关键取舍

| 项 | 值 | 理由 |
|---|---|---|
| `flow_offloading` / `_hw` | 0 / 0 | TPROXY 在 prerouting 接管，卸载走 forward 快速路径；UDP/QUIC + fullcone 组合下有边界，历史事故是「代理时通时断」 |
| 峰值吞吐 | 交给多核分流 + fq_codel | 若要压满 2.5G：`uci set firewall.@defaults[0].flow_offloading=1 && uci commit firewall && fw4 reload`（自担风险） |
| `tcp_tw_reuse` | 1 | 含 loopback 复用有 TIME_WAIT 串号风险 |
| `tcp_fastopen` | 1 | 路由器不做 TFO 服务端 |
| `dnsmasq.dns_redirect` | 0 | 交给 nikki 的 `:53 → :1053` 劫持，避免双重 |
| `min_cache_ttl` | 300 | 避免 CDN IP 被锁 1 小时 |
| LAN IPv6 | 全关 | 终端双栈会并发探测 v6，被 REJECT 后应用体验变差（微信发图转圈等）；WAN v6 仍给节点用 |

## 4. 流量接管范围（实测口径）

接管：LAN IPv4 的 TCP/UDP（含 QUIC 之外的 UDP）、路由器自身 TCP/UDP、所有 DNS（v4/v6 的 53 端口被劫持到 mihomo）。

不接管（设计如此）：

- LAN 内部互访、`loopback`、RFC1918、组播等 `reserved_ip` 命中流量；
- LAN 的 IPv6 出网（直接 REJECT，不做代理）；
- 打 `DSCP=4` 标记的包（`bypass_dscp=4`）；
- LAN → 路由器自身的管理流量（INPUT，不走 TPROXY）。

核对方法：`curl -u <user:pass> http://127.0.0.1:9090/connections` 看源 IP 与 `chains`，或看 nft `tproxy` 规则计数。

## 5. 刷机后要做的事

1. 配好 PPPoE（构建时已有开关，账号密码由 workflow 输入）。
2. 写入订阅（二选一）：
   - 运维脚本 `~/.ssh/r5c-optimized/deploy.sh`（推荐，含校验与回滚）；
   - LuCI → 服务 → Nikki → 订阅，粘两条 URL：
     - ✈️ 带机场：`…?device=nikki&dns=doh&ipv6=true`
     - 🏠 只含自建：`…?device=nikki&dns=doh&ipv6=true&profile=simple`
3. 验证（全部应通过）：

```sh
/etc/init.d/nikki status
mihomo -t -d /etc/nikki/run -f /etc/nikki/run/config.yaml
grep -c "NETWORK,UDP" /etc/nikki/run/config.yaml            # 期望 1
nft list ruleset | grep -c tproxy                            # ≥1
curl -s -m 10 https://ipinfo.io/ip                           # 节点 IP，不是 PPPoE 地址
uci get dhcp.lan.ra                                          # disabled
tc qdisc show dev pppoe-wan                                  # fq_codel
```

## 6. 回滚

本仓库的改动都属于「下次刷机生效」，不影响当前运行的设备。若刷入后要临时回退：

```sh
uci set firewall.@defaults[0].flow_offloading=1; uci commit firewall; fw4 reload   # 恢复 offload
uci set dhcp.lan.ra=server; uci set network.lan.ip6assign=60                       # 恢复 LAN IPv6
uci set nikki.config.enabled=0; uci commit nikki; /etc/init.d/nikki stop           # 停代理
```

## 7. 已知坑

- 旧镜像把 conntrack/BBR 写在 `/etc/sysctl.d/`，与本仓库的标记块冲突；`97-sysctl-network.sh` 会自动删除它们。
- nikki 的控制口默认 `[::]:9090`、`allow-lan=1`、端口 7890/8080/1080，属于局域网可达面；需要收紧时在设备上执行：
  ```sh
  uci set nikki.mixin.allow_lan=0
  uci set nikki.mixin.api_listen='127.0.0.1:9090'
  uci commit nikki && /etc/init.d/nikki restart
  ```
  TPROXY 不依赖这些端口，关闭不影响全屋代理。
