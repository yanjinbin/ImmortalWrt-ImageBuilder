# 固定版本安装包

`luci-app-uugamebooster-1.1-r1.apk` 是此前固件使用的原版 UU LuCI 安装包。上游仓库于 2026-10-25 检查时返回 404，因此将本地缓存中的相同文件归档，避免固件构建依赖失效的下载地址。

- 原项目：<https://github.com/lmq8267/luci-app-uugamebooster>
- 原发布地址：<https://github.com/lmq8267/luci-app-uugamebooster/releases/download/1.1/luci-app-uugamebooster-1.1-r1.apk>
- SHA256：`e63161f9cc178751a38a09a15d3fddf5d88724ee6deca98438efbdfcdc68c20e`

该文件与原工作流固定的 SHA256 一致，未修改版本或内容。工作流先校验并复制安装包，再由 `shell/repair-uugamebooster.py` 沿用原有流程修复离线安装脚本，生成 `1.1-r2`。归档不包含网易加速器二进制；启用插件后仍由插件下载。
