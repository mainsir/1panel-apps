# 1Panel Apps

个人维护的 [1Panel](https://1panel.cn/) **本地应用**仓库，便于多台服务器同步安装与备份移植。

## 当前应用

| 应用 | 说明 | 版本 |
|---|---|---|
| [3proxy](./apps/3proxy) | 轻量 HTTP / SOCKS5 代理（环境变量配置） | 1.0.0 |
| [gitea-sqlite](./apps/gitea-sqlite) | 轻量 Git 代码托管（SQLite 单容器，无需 MySQL） | 1.27.3 |
| [kasmweb-chrome](./apps/kasmweb-chrome) | Web 端高清 Chrome 浏览器（KasmVNC 串流，支持数据持久化） | 1.16.0 |
| [sing-box-reality](./apps/sing-box-reality) | 基于 sing-box 的 VLESS Reality 入站（host 网络） | 1.0.0 |

## 安装到 1Panel（本地应用）

默认 1Panel 安装路径为 `/opt/1panel`，请按实际路径调整。

### 方式一：临时目录一键同步（推荐手动）

每次重新 clone 最新代码，拷贝后清理临时目录：

```bash
rm -rf /tmp/1panel-apps \
  && git clone --depth 1 https://github.com/mainsir/1panel-apps.git /tmp/1panel-apps \
  && mkdir -p /opt/1panel/resource/apps/local \
  && cp -rf /tmp/1panel-apps/apps/* /opt/1panel/resource/apps/local/ \
  && rm -rf /tmp/1panel-apps
```

说明：

- **clone 前** `rm -rf`：避免目录已存在导致 clone 失败，并保证拉到最新
- **clone / cp**：下载并写入 1Panel 本地应用目录
- **cp 后** `rm -rf`：清理 `/tmp`，与是否最新无关，只是打扫现场

然后在 1Panel：**应用商店 → 更新应用列表**，在「本地」分类中安装。

> `cp -rf` 只会覆盖/新增本仓库里的应用。若仓库已删除某个 app（例如 karakeep），服务器上需手动删掉对应目录：  
> `rm -rf /opt/1panel/resource/apps/local/<app-key>`

### 方式二：计划任务同步（长期目录 + pull）

适合定时任务，不必每次全量 clone：

```bash
#!/bin/bash
set -e
REPO_DIR=/opt/1panel-apps
LOCAL_DIR=/opt/1panel/resource/apps/local

if [ ! -d "$REPO_DIR/.git" ]; then
  git clone https://github.com/mainsir/1panel-apps.git "$REPO_DIR"
else
  git -C "$REPO_DIR" pull --ff-only
fi

mkdir -p "$LOCAL_DIR"
cp -rf "$REPO_DIR"/apps/* "$LOCAL_DIR"/
echo "synced at $(date)"
```

也可直接用仓库脚本：`bash scripts/sync-to-1panel.sh`。

将脚本加入 1Panel 计划任务（例如每天一次），同步后手动或脚本触发「更新应用列表」。

## 目录结构

```text
apps/<app-key>/
  logo.png
  README.md
  data.yml
  <version>/
    data.yml
    docker-compose.yml
    data/
    scripts/          # 可选
```

规范说明见：[1Panel本地应用制作规范.md](./1Panel本地应用制作规范.md)

## 说明

- 仓库只放**应用定义包**（compose / data.yml / README），不包含运行时数据与真实密钥。
- 安装时在面板表单中填写端口、密码、Token 等。
- 网络默认使用 bridge + `1panel-network`；`sing-box-reality` 因需直接监听宿主机端口使用 host 模式。

## License

MIT
