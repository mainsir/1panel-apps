## 产品介绍

本应用基于官方镜像 [`tobyxdd/hysteria`](https://hub.docker.com/r/tobyxdd/hysteria) 部署 **Hysteria2**（QUIC / UDP）。TLS 使用宿主机已有的 Let's Encrypt 证书（例如 1Panel OpenResty 站点目录下的 `ssl`），并开启 Hysteria2 内置 **masquerade** 伪装：普通访客看到的是正常 HTTPS 站点内容（默认反代到微软官网），而不是空白 404。

适合已经有独立域名与证书的 1Panel / DMIT 场景。协议走 **UDP**，与同机 OpenResty 的 **TCP 443** 可以并存；强烈建议使用 **UDP 443**，并在防火墙/安全组放行。

> **隔离提醒**：请使用**单独子域名**部署本代理，不要与 Bitwarden / 密码库、邮箱等敏感服务共用同一域名或同一反代站点，降低被关联与扫描误伤的风险。

## 主要功能

- 协议：Hysteria2（UDP / QUIC），密码认证
- TLS：挂载宿主机证书目录（只读），证书文件名可配（默认 `fullchain.pem` / `privkey.pem`）
- 伪装：`proxy`（默认反代公共站点）或 `file`（应用内置静态页 `/www/masq`）
- 首次启动自动生成密码并写入 `keys.env`；表单留空时重启沿用；填写新密码会覆盖
- 每次启动按表单生成 `config.yaml`，并在 `client.txt` 写入可导入的 `hysteria2://` 链接
- 可选上下行带宽限制；默认 `ignoreClientBandwidth: true`
- `network_mode: host`，便于占用 UDP 443；架构：amd64 / arm64

## 默认参数

| 项目 | 默认值 | 说明 |
|---|---|---|
| UDP 端口 | 443 | 理想伪装端口；被占用时可改 8443 等 |
| 域名 | 安装时填写 | 分享链接与 SNI |
| 密码 | 留空自动生成 | 保存在 `keys.env` |
| 证书目录 | `/opt/1panel/www/sites/your.domain/ssl` | 改成真实站点目录 |
| 伪装类型 | proxy | 也可选 file |
| 伪装目标 | `https://www.microsoft.com` | proxy 模式 |
| 忽略客户端带宽 | true | |
| 节点备注 | Hysteria2 | |
| 时区 | Asia/Shanghai | |

## 使用说明

1. 准备一个**专用子域名**（例如 `hy2.example.com`），在 Cloudflare/DNS 解析到本机，并在 1Panel OpenResty 为该站点申请 Let's Encrypt。证书目录通常类似：  
   `/opt/1panel/www/sites/hy2.example.com/ssl`
2. 安装本应用时填写：域名、上述证书目录、UDP 端口（建议 443）。密码可留空。
3. 在云厂商安全组 / 本机防火墙放行该 **UDP** 端口（TCP 不必为本应用单独开放）。
4. 启动后打开数据目录里的 `client.txt`，把 `hysteria2://` 链接导入客户端。
5. 伪装自测：用支持 HTTP/3 的浏览器访问 `https://你的域名:端口`（Chrome 可用 `--origin-to-force-quic-on=域名:端口`），应看到伪装站点内容，而不是代理特征页。

### 与 OpenResty 共存

- OpenResty 继续占用 **TCP 80/443** 做网站与证书续期。
- Hysteria2 占用 **UDP 443**（或其它 UDP 端口）。二者不冲突。
- 本应用**默认不**开启 `listenHTTP` / `listenHTTPS`（TCP 伪装），避免与 OpenResty 抢端口。QUIC 上的 masquerade 已足够应对常见探测。

### 防火墙示例

```bash
# nftables / iptables 示例：放行 UDP 443
ufw allow 443/udp
# 或
firewall-cmd --add-port=443/udp --permanent && firewall-cmd --reload
```

## 数据目录

| 路径 | 说明 |
|---|---|
| `./data/keys.env` | 密码（自动保存） |
| `./data/config.yaml` | Hysteria2 运行配置 |
| `./data/client.txt` | 节点链接与客户端参数 |
| `./www/` | file 伪装模式的静态站点 |

卸载前请用 1Panel 备份，或另行保存 `data` 目录。卸载可能删掉实例目录；重装若未保留 `keys.env` 会生成新密码，旧链接失效。

## 运行镜像

`tobyxdd/hysteria:v2.13.0`
