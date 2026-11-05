## 产品介绍

本应用提供 HTTP 和 SOCKS5 代理服务，使用安装表单配置账号、密码、端口和 DNS。镜像由 [tarampampam/3proxy-docker](https://github.com/tarampampam/3proxy-docker) 维护。

## 默认端口

| 用途 | 宿主机端口 | 容器端口 |
|---|---|---|
| HTTP 代理 | 3128 | 3128 |
| SOCKS5 代理 | 1080 | 1080 |

## 使用说明

安装时填写代理账号和密码。在客户端中选择 HTTP 或 SOCKS5，输入服务器地址、对应端口和认证信息。

最大连接数按协议分别设置，可选 128、256、512 或 1024。容器文件描述符上限为 8192。应用加入 `1panel-network`，可与同网络中的应用通信。

## 配置与备份

本应用使用环境变量生成配置，不包含业务数据挂载目录。备份和迁移时保留实例的 Compose 文件及 `.env` 参数文件。

## 运行环境

- 镜像：`ghcr.io/tarampampam/3proxy:2.3.0`
- 架构：amd64、arm64、arm/v7
