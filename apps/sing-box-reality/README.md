## 产品介绍

本应用基于 [sing-box](https://sing-box.sagernet.org/) 部署 **VLESS** 入站，并启用 **Reality** TLS。  
适用于需要安全传输通道的场景，通过 1Panel 本地应用一键安装与管理。

## 主要功能

- 协议：VLESS over TCP，TLS Reality，Vision（`xtls-rprx-vision`）
- 首次启动自动生成 UUID、Reality 密钥对与 shortId
- 自动输出客户端连接信息（`share.link` / `client.txt`）
- 采用 host 网络模式；支持架构：amd64

## 默认参数

| 项目 | 默认值 |
|---|---|
| 监听端口 | 38443 |
| 伪装域名 (SNI) | www.nvidia.com |
| Reality 握手目标 | www.nvidia.com:443 |
| 客户端指纹 | chrome |

## 使用说明

1. 安装时填写服务器公网 IP 或域名作为客户端连接地址。
2. 启动后查看数据目录中的 `share.link` 或 `client.txt`，导入至客户端。
3. 修改端口、SNI 或握手目标后，请重新获取并导入连接信息。

## 数据目录

| 路径 | 说明 |
|---|---|
| `./data/keys.env` | UUID 与 Reality 密钥（请妥善保管） |
| `./data/config.json` | sing-box 运行配置 |
| `./data/share.link` | 标准分享链接 |
| `./data/client.txt` | 客户端参数说明 |

## 运行镜像

`ghcr.io/sagernet/sing-box:v1.13.14`
