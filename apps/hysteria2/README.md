## 产品介绍

本应用基于官方镜像 [`tobyxdd/hysteria`](https://hub.docker.com/r/tobyxdd/hysteria) 部署 **Hysteria2**（QUIC / UDP）。TLS 使用宿主机已有的 Let's Encrypt 证书，并开启内置 **masquerade** 伪装（默认反代公共站点）。

协议走 **UDP**，可与同机 OpenResty 的 **TCP 443** 并存；建议 **UDP 443**。自 **1.0.2** 起，安装表单中的 UDP 端口不会按 1Panel 的 TCP 端口占用规则检查，OpenResty 已监听 TCP 443 时仍可安装。

> **隔离提醒**：请使用**单独子域名**，不要与密码库 / 邮箱等敏感服务共用同一域名。

## 表单（已精简）

| 字段 | 说明 |
|---|---|
| UDP 端口 | 默认 443 |
| 域名 | SNI / 分享链接 |
| 密码 | 留空自动生成 |
| 证书目录 | 宿主机 `ssl` 目录（固定读 `fullchain.pem` / `privkey.pem`） |
| 伪装反代目标 | 默认 `https://www.microsoft.com` |
| 【高级】SOCKS5 落地 | 全部留空 = **直连**；填写 host+port 后走 SOCKS5 出口 |

已从表单移除：时区、证书/私钥文件名、伪装类型、带宽限制、忽略客户端带宽、节点备注名。需要时可直接改实例目录里的 `data/config.yaml`（或改 `scripts/entrypoint.sh` 后重建）。

## 使用说明

1. 专用子域名 + 1Panel OpenResty 申请 LE；证书目录类似 `/opt/1panel/www/sites/hy2.example.com/ssl`
2. 安装时填域名、证书目录、UDP 443；密码可留空；SOCKS5 默认全空（直连）
3. 放行 **UDP** 端口；启动后看 `data/client.txt` 导入链接

从 1.0.0 / 1.0.1 升级后，容器仍按原来的 UDP 端口监听。在「参数」里重新保存前，新字段可能显示默认 443；若之前不是 443，请先改回原端口再保存。

## 数据目录

| 路径 | 说明 |
|---|---|
| `./data/keys.env` | 密码 |
| `./data/config.yaml` | 运行配置（可手动微调） |
| `./data/client.txt` | 节点链接 |

## 镜像

`tobyxdd/hysteria:v2.13.0`
