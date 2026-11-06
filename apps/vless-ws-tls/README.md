## 产品介绍

基于 [sing-box](https://sing-box.sagernet.org/) 的 VLESS + WebSocket 代理服务，通过 OpenResty 或 nginx 提供 TLS 加密连接。支持直连和 SOCKS5 出口，自动生成客户端导入链接。

## 安装与使用

1. 准备已解析到服务器并配置 HTTPS 证书的域名。
2. 安装 `1.0.5`，填写域名，端口与 WS 路径使用默认值。直连时 SOCKS5 参数留空；使用代理时填写出口地址和端口，按需填写账号、密码。
3. 在域名对应的 HTTPS 站点中添加下方反向代理配置。
4. 启动后，打开实例目录中的 `data/client.txt`，将节点链接导入客户端。默认节点名称为 `VLESS-WS-TLS`，连接端口为 `443`。

## 反向代理

以下示例适用于默认端口和路径。修改安装参数后，请同步调整对应配置。反向代理需能访问宿主机的 `127.0.0.1:18443`。

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

## 数据与凭据

| 文件 | 用途 |
|---|---|
| `data/client.txt` | 客户端参数与导入链接 |
| `data/keys.env` | UUID 凭据 |
| `data/config.json` | 自动生成的运行配置 |

每个实例使用一个 UUID，可供多台设备共用。保留 `data/keys.env` 时，重启和重建容器不会更换 UUID。升级或卸载前请备份 `data` 目录。
