# 1Panel Apps

个人维护的 [1Panel](https://1panel.cn/) **本地应用**仓库，便于多台服务器同步安装与备份移植。

## 当前应用

| 应用 | 说明 | 版本 |
|---|---|---|
| [3proxy](./apps/3proxy) | 轻量 HTTP / SOCKS5 代理（环境变量配置） | 1.0.0 |
| [embyproxy](./apps/embyproxy) | Emby 代理服务 | 1.0.0 |

## 安装到 1Panel（本地应用）

默认 1Panel 安装路径为 `/opt/1panel`，请按实际路径调整。

### 方式一：直接拷贝

```bash
git clone https://github.com/mainsir/1panel-apps.git /tmp/1panel-apps
cp -rf /tmp/1panel-apps/apps/* /opt/1panel/resource/apps/local/
```

然后在 1Panel：**应用商店 → 更新应用列表**，在「本地」分类中安装。

### 方式二：计划任务同步

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

将以上脚本加入 1Panel 计划任务（例如每天一次），同步后手动或脚本触发「更新应用列表」。

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
- 网络默认使用 bridge + `1panel-network`，不是 host 模式（除非应用另有说明）。

## License

MIT
