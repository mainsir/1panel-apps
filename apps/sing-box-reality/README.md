## 产品介绍

本应用基于 [sing-box](https://sing-box.sagernet.org/) 部署 **VLESS** 入站，并启用 **Reality** TLS。  
适用于需要安全传输通道的场景，通过 1Panel 本地应用一键安装与管理。

## 主要功能

- 协议：VLESS over TCP，TLS Reality，Vision（`xtls-rprx-vision`）
- 首次启动自动生成 UUID、Reality 密钥对与 shortId
- 自动输出客户端连接信息与节点链接（`client.txt`）
- 支持可选出口代理：可配置上游 Socks5 节点作为出口（留空默认直连本机）
- 采用 host 网络模式；支持架构：amd64

## 默认参数

| 项目 | 默认值 | 说明 |
|---|---|---|
| 监听端口 | 38443 | Reality 协议服务端口 |
| 伪装域名 (SNI) | www.nvidia.com | 伪装网站，握手自动同步该域名 443 |
| 客户端指纹 | chrome | 默认最佳伪装指纹 |
| 出口代理 (Socks5) | 留空（默认直连本机） | 可选，用于切换出口 IP |

## 使用说明

1. 安装时可直接使用默认参数一键安装，或按需自定义监听端口与伪装域名。
2. 启动后查看数据目录中的 `client.txt`，复制节点链接一键导入客户端。
3. 首次启动会自动生成专属安全 UUID 与 Reality 密钥对，并自动持久化保存在 `keys.env` 中。
4. 如需指定出口 IP（如解锁流媒体或使用住宅代理），可在参数中填写出口代理地址与端口。

## 数据目录

| 路径 | 说明 |
|---|---|
| `./data/keys.env` | UUID 与 Reality 密钥（自动持久化保存） |
| `./data/config.json` | sing-box 运行配置 |
| `./data/client.txt` | 客户端节点链接及详细参数说明 |

## 运行镜像

`ghcr.io/sagernet/sing-box:v1.13.14`
