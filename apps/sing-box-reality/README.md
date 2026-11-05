## 产品介绍

本应用基于 [sing-box](https://sing-box.sagernet.org/) 部署 **VLESS + WebSocket** 入站。TLS 在前置 OpenResty 或 nginx 上终止，sing-box 只监听本机，配置里没有 Reality。

适合已经有网站和 Let's Encrypt 证书的 1Panel：把一条隐藏的 WebSocket 路径反代到本机端口即可。客户端连接域名的 443，不直连 sing-box。

## 主要功能

- 协议：VLESS over WebSocket，用户只有 UUID，不启用 Vision flow
- 传输路径可配，早期数据 2048 字节，头为 `Sec-WebSocket-Protocol`
- sing-box 不配置 TLS / Reality；证书由前置反代提供
- 首次启动生成并保存 UUID，重启和修改参数时沿用已有 UUID
- 每次启动按表单生成 `config.json`，并在 `client.txt` 写入可导入的节点链接
- 可选出口：填写 Socks5 后入站流量从该代理出去；留空则直连
- host 网络，固定监听 `127.0.0.1`，便于同机 OpenResty 访问；架构：amd64
- 自 **1.0.3** 起，安装表单不再包含时区、监听地址和节点备注。容器使用镜像默认时区；入站固定 `127.0.0.1`；分享链接备注固定为 `SingBox-WS`

## 默认参数

| 项目 | 默认值 | 说明 |
|---|---|---|
| 本机监听端口 | 18443 | 只给反代使用，客户端不要填这个端口 |
| 监听地址 | 127.0.0.1 | 固定只对本机开放，表单不可改 |
| WebSocket 路径 | `/cdn-cgi/assets/v7kQm2pLx9nR` | 建议改成自己的隐藏路径 |
| 客户端域名 | 安装时填写 | 分享链接、SNI 和 Host 都使用该域名 |
| 节点备注 | SingBox-WS | 固定写入分享链接，表单不可改 |
| 指纹 | chrome | 写在分享链接里 |
| SOCKS5 落地 | 留空（直连） | 地址和端口留空则直连；账号和密码可选 |

## 使用说明

1. 安装时填写已经解析到这台机器、并且已经在 OpenResty / nginx 上申请了证书的域名。
2. 在该网站配置里加上下面的 WebSocket 反代。`location` 必须与 WebSocket 路径一致，`proxy_pass` 的端口必须与本机监听端口一致。
3. 启动后打开数据目录里的 `client.txt`，把节点链接导入客户端。客户端地址是 **域名:443**。
4. 从 1.0.1（Reality）升级时会保留 `keys.env` 里的 UUID，不再使用 Reality 密钥。配好反代后，用新的 `client.txt` 更新客户端。原来的 Reality 链接不能继续用。

卸载前请用 1Panel 备份，或另行保存 `data` 目录。卸载可能删掉实例目录；重装会生成新 UUID，旧链接失效。

### OpenResty / nginx

TLS 在网站的 443 上终止，使用该站点已有的 Let's Encrypt 证书。下面按默认路径和端口举例。改过表单时，把路径和端口换成实际值。

OpenResty 需要能访问宿主机上的 `127.0.0.1`（1Panel 的 OpenResty 使用 host 网络时就是这样）。不要把本机监听端口暴露到公网。

```nginx
location = /cdn-cgi/assets/v7kQm2pLx9nR {
    proxy_pass http://127.0.0.1:18443;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 300s;
}
```

### 出口代理

需要更换出口 IP 时，同时填写 SOCKS5 落地地址和端口。留空则直连。需要认证时，账号和密码一起填。端口范围是 1–65535。只填一半时容器会拒绝启动。

## 密钥与版本升级

`1.0.4` 保留 `1.0.3` 的 WebSocket 协议、精简表单和本机监听方式，修复 UUID 持久化。已有 `keys.env` 只读取，缺失或无效的 UUID 会阻止启动；首次生成使用原子发布，写入失败不会清空原文件。运行配置通过校验后再替换。

升级前备份 `data` 目录，并在 1Panel 中选择 `1.0.4`。从旧版 Reality 迁移时保留 UUID 和原密钥文件，连接方式仍需按下方说明切换为 WebSocket。公网 IPv4/IPv6 监听由前置 OpenResty 或 nginx 提供，后端保持 `127.0.0.1`。

## 数据目录

| 路径 | 说明 |
|---|---|
| `./data/keys.env` | UUID（自动保存） |
| `./data/config.json` | sing-box 运行配置 |
| `./data/client.txt` | 节点链接和客户端参数 |

## 运行镜像

`ghcr.io/sagernet/sing-box:v1.13.14`
