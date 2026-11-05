## 产品介绍

基于 [sing-box](https://sing-box.sagernet.org/) 的 SOCKS5 代理，适合内存和进程数受限的小规格 VPS。sing-box 按事件处理连接，默认要求账号密码。

本应用替代原来的 3proxy。不再单独提供 HTTP 代理端口。

## 主要功能

- SOCKS5 入站，账号密码认证，出口直连
- 可选同端口 HTTP：入站类型选 `SOCKS5 + HTTP`（sing-box `mixed`）
- 表单配置端口、账号、密码、日志级别和时区
- 每次启动按环境变量生成配置，改参数后重启即生效
- 默认加入 `1panel-network`；LXC 端口转发无效时可选 host 网络
- 异常退出自动重启，文件描述符上限 65535

## 默认参数

| 项目 | 默认值 | 说明 |
|---|---|---|
| 端口 | 10001 | bridge 下宿主机与容器使用同一端口 |
| 账号 | proxy | 必填 |
| 密码 | 随机 | 在默认值后追加随机串，请自行保存 |
| 入站 | SOCKS5 | 可选 SOCKS5 + HTTP |
| 日志 | warn | |
| 时区 | Asia/Shanghai | |
| 网络 | bridge | 安装时可选 host，安装后不可改 |

## 使用说明

- SOCKS5：`socks5://账号:密码@服务器IP:端口`
- 入站为 SOCKS5 + HTTP 时，HTTP 使用同一地址：`http://账号:密码@服务器IP:端口`

请勿把代理暴露到公网且不设认证。账号或密码为空时容器拒绝启动。

### 网络模式

默认 **bridge**：加入外部网络 `1panel-network`，并把表单端口发布到宿主机（TCP 与 UDP）。

部分 LXC NAT 环境无法转发 Docker 发布端口。安装时把网络模式选为 **host**。host 模式不加入 `1panel-network`，也不做端口映射，进程直接监听宿主机上的该端口。

网络模式只在安装和升级时写入 compose。参数页不能修改此项；选错请卸载后重装。升级会按已保存的模式重新套用，不会把 host 装回 bridge。

若宿主机不允许把文件描述符上限提到 65535，容器会启动失败。把 compose 里的 `nofile` 调低后重新创建容器即可。

### 从 3proxy 迁移

停用旧实例后再安装本应用。需要 HTTP 代理时选择 `SOCKS5 + HTTP`，与 SOCKS5 共用端口和账号。商店同步不会删除服务器上的旧包，请手动执行：

`rm -rf /opt/1panel/resource/apps/local/3proxy`

已经安装的 3proxy 实例不会被自动卸载。

## 数据目录

| 路径 | 说明 |
|---|---|
| `./data/config.json` | 启动时生成的运行配置，含账号密码，权限 600 |

## 运行镜像

`ghcr.io/sagernet/sing-box:v1.13.21`
