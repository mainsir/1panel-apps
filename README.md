# 1Panel 本地应用仓库

本仓库提供适用于 1Panel 本地应用商店的第三方应用包。应用配置、安装表单和生命周期脚本随版本管理。

[English](README_en.md) · [应用制作规范](1Panel本地应用制作规范.md)

## 环境要求

- 已安装 1Panel 的 Linux 主机。
- Bash、Git、rsync 和 flock（由 util-linux 提供）。
- 对本地应用商店目录具有写入权限。

Debian / Ubuntu 可使用以下命令安装同步依赖：

```bash
apt-get install -y git rsync util-linux curl
```

## 同步应用

下载并执行同步脚本：

```bash
curl -fsSL https://raw.githubusercontent.com/mainsir/1panel-apps/main/scripts/sync-to-1panel.sh \
  -o /tmp/1panel-apps-sync.sh && bash /tmp/1panel-apps-sync.sh
```

脚本每次从指定仓库的默认分支获取应用包，不会读取或更新 `/opt/1panel-apps` 中的现有工作区。获取失败时终止同步。

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `REPO_URL` | `https://github.com/mainsir/1panel-apps.git` | 应用仓库地址，也支持本地 Git 仓库路径 |
| `LOCAL_DIR` | `/opt/1panel/resource/apps/local` | 1Panel 本地应用商店目录 |

使用其他来源或目录：

```bash
REPO_URL=https://github.com/example/apps.git \
LOCAL_DIR=/opt/1panel/resource/apps/local \
bash /tmp/1panel-apps-sync.sh
```

使用已克隆的本地仓库：

```bash
REPO_URL=/opt/1panel-apps bash /opt/1panel-apps/scripts/sync-to-1panel.sh
```

本地来源只同步已提交的内容。`USE_TMP` 参数已移除，所有来源均通过临时克隆目录读取。

### 同步范围

- 按源仓库中的应用 Key 更新同名目录，删除该目录中已移除的版本和文件。
- 不修改其他应用 Key 的目录；不要让不同来源使用相同的应用 Key。
- 已从源仓库整体删除的应用目录保留，由管理员确认后手动清理。
- 不修改已安装实例的配置或数据。实例升级需在 1Panel 中单独执行。
- 同一目标目录不允许并发同步。部分应用同步失败时脚本返回非零，已完成的应用不会回滚，可修复原因后重新执行。

`LOCAL_DIR` 应指向应用商店目录，不应指向已安装实例目录。对同名应用包的本地修改会被同步覆盖。

## 安装与升级

1. 完成同步后，在 1Panel 中打开「应用商店」。
2. 点击「更新应用列表」，切换到「本地」分类。
3. 选择应用并填写安装参数。

已有实例在备份后通过面板升级。修改同版本安装包不会自动更新已有实例；应用行为变更应发布新的包版本。

如需定期同步，可在 1Panel「计划任务」中创建 Shell 任务，使用上述下载并执行命令。

## 应用列表

| 应用 | 架构 | 说明 |
|---|---|---|
| [sing-box SOCKS5](apps/sing-box-socks5) | amd64、arm64、arm/v7 | SOCKS5 代理，可选同端口 HTTP |
| [Gitea SQLite](apps/gitea-sqlite) | amd64、arm64 | 使用 SQLite 的单容器 Git 托管服务 |
| [Kasm Chrome](apps/kasmweb-chrome) | amd64 | 通过浏览器访问 Chrome 桌面，持久化用户目录 |
| [VLESS WS TLS](apps/vless-ws-tls) | amd64 | VLESS WebSocket 入站，由前置反向代理提供 TLS |
| [Hysteria2](apps/hysteria2) | amd64、arm64 | 基于 QUIC / UDP 的代理服务 |

## 校验

本地与 CI 使用相同的包校验入口：

```bash
python3 -m pip install pyyaml pillow
python3 scripts/validate-apps.py
python3 -m unittest discover -s tests -v
```

测试使用临时目录，不同步实际应用商店。设置 `SING_BOX_BINARY` 为包中镜像对应版本的 sing-box 可执行文件路径后，还会检查真实配置及 IPv4/IPv6 TCP 监听；未设置且系统未安装时跳过真实二进制测试。完整安装和升级仍需在 1Panel 中验证。

制作应用前请阅读[应用制作规范](1Panel本地应用制作规范.md)。

## 许可证

本仓库使用 [MIT License](LICENSE)。上游软件和容器镜像遵循各自许可证。
