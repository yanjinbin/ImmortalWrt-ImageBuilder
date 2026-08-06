#!/bin/sh
# 默认 root 密码 666666 (仅首次启动设置; 之后用户可在 LuCI 系统->管理权 修改)
printf '666666\n666666\n' | passwd root >/dev/null 2>&1

exit 0
