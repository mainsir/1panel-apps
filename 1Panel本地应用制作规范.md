# 1Panel 本地应用制作规范

> 适用范围：本仓库 `apps/` 下的应用，以及 1Panel 本地应用商店 `/opt/1panel/resource/apps/local`。
> 目标：格式和官方商店一致，可以整包同步到多台 1Panel，安装、升级、备份时行为可预期。
>
> 核对来源（2026-10 核对）：
> - 官方 Wiki：[如何提交自己想要的应用](https://github.com/1Panel-dev/appstore/wiki/%E5%A6%82%E4%BD%95%E6%8F%90%E4%BA%A4%E8%87%AA%E5%B7%B1%E6%83%B3%E8%A6%81%E7%9A%84%E5%BA%94%E7%94%A8)
> - 官方应用仓库 [1Panel-dev/appstore](https://github.com/1Panel-dev/appstore)（`dev` 分支，参考 `frps`、`uptime-kuma`、`halo`）
> - 官方封装工具 [1Panel-appstore-skills](https://github.com/1Panel-dev/1Panel-appstore-skills)：`references/appstore-format.md`、`references/review-checklist.md`、`scripts/validate_app_package.py`

---

## 1. 目录结构

```text
apps/<app-key>/
├── logo.png                 # 必需，180×180，建议 ≤ 50 KB（保持清晰不失真）
├── README.md                # 必需，中文
├── README_en.md             # 推荐，英文
├── data.yml                 # 必需，应用声明
└── <version>/               # 必需，版本目录，不能以 v 开头
    ├── data.yml             # 必需，安装表单（无表单也要有 formFields 字段）
    ├── docker-compose.yml   # 必需
    ├── data/.gitkeep        # 需要持久化目录时提供
    └── scripts/             # 可选，不需要就不建
        ├── init.sh
        ├── upgrade.sh
        └── uninstall.sh
```

命名规则：

| 项 | 规则 | 示例 |
|---|---|---|
| `app-key` | 小写英文、数字、`-`；与目录名、`additionalProperties.key` 一致 | `sing-box-reality` |
| 版本目录 | 去掉 `v` 前缀；优先与上游镜像版本一致 | 镜像 `v1.13.14` → 目录 `1.13.14` |
| 升级 | 1Panel 按版本目录识别新版本，新增目录即为新版本 | `1.13.14/`、`1.14.2/` |

> 官方商店用上游版本号命名版本目录。自封装应用（版本号和镜像无关）可以用 `1.0.0` 起步，但每次改镜像版本都要新建目录，不要原地覆盖。

---

## 2. 根目录 `data.yml`

```yaml
name: Uptime Kuma
tags:
  - 实用工具
title: 一款精美的自托管监控工具
description: 一款精美的自托管监控工具
additionalProperties:
  key: uptime-kuma
  name: Uptime Kuma
  tags:
    - Tool
  shortDescZh: 一款精美的自托管监控工具
  shortDescEn: A fancy self-hosted monitoring tool
  description:
    en: A fancy self-hosted monitoring tool
    zh: 一款精美的自托管监控工具
  type: website
  crossVersionUpdate: true
  limit: 0
  recommend: 0
  website: https://uptime.kuma.pet/
  github: https://github.com/louislam/uptime-kuma
  document: https://github.com/louislam/uptime-kuma/wiki
  architectures:
    - amd64
    - arm64
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` / `tags` / `title` / `description`（顶层） | 是 | 官方包都有这些字段，照写 |
| `additionalProperties.key` | 是 | 与目录名一致 |
| `additionalProperties.name` | 是 | 显示名称 |
| `additionalProperties.tags` | 是 | 取值见下表，可多个 |
| `shortDescZh` / `shortDescEn` | 是 | 短描述，中文不超过 30 字 |
| `description` | 是 | 本仓库只写 `en` 和 `zh`。官方商店要求 10 种语言（另加 `zh-Hant` `ja` `ko` `ru` `es-es` `pt-br` `ms` `tr`），本地应用不需要 |
| `type` | 是 | `website` / `runtime` / `tool`，只能选一个 |
| `crossVersionUpdate` | 是 | 是否允许跨大版本升级 |
| `limit` | 是 | 最多安装几个实例，`0` 不限；端口或密钥固定的应用填 `1` |
| `architectures` | 是 | 以镜像 manifest 为准：`amd64` `arm64` `arm/v7` 等 |
| `website` / `github` / `document` | 推荐 | 上游链接 |
| `recommend` | 可选 | 排序权重，本地应用填 `0` |
| `batchInstallSupport` | 可选 | 官方新包中出现，本地一般不需要 |

`tags` 取值：

| key | 含义 |
|---|---|
| `WebSite` | 建站 |
| `Server` | Web 服务器 |
| `Runtime` | 运行环境 |
| `Database` | 数据库 |
| `Tool` | 工具 |
| `CI/CD` | CI/CD |
| `DevOps` | 开发与运维（官方 Gitea 使用） |
| `Local` | 本地 |

`type` 取值：

| type | 说明 |
|---|---|
| `website` | 可在「网站」中一键部署（WordPress、Halo 等） |
| `runtime` | MySQL、OpenResty、Redis 等基础组件 |
| `tool` | phpMyAdmin、Jenkins、代理等工具 |

---

## 3. 版本目录 `data.yml`（安装表单）

```yaml
additionalProperties:
  formFields:
    - default: 3001
      edit: true
      envKey: PANEL_APP_PORT_HTTP
      labelEn: Port
      labelZh: 端口
      required: true
      rule: paramPort
      type: number

    - default: admin
      edit: true
      envKey: ADMIN_PASSWORD
      labelEn: Password
      labelZh: 密码
      required: true
      random: true
      rule: paramComplexity
      type: password
```

字段说明：

| 字段 | 说明 |
|---|---|
| `envKey` | 写入 `.env`，在 compose 中用 `${envKey}` 引用 |
| `default` | 默认值 |
| `required` | 是否必填 |
| `edit` | 安装后能否在「参数」中修改 |
| `random` | 在默认值后追加随机串，密码、数据库名常用 |
| `labelZh` / `labelEn` | 旧写法，仍兼容 |
| `label` | 新写法，多语言映射（官方新包使用）；本仓库只写 `labelZh` / `labelEn` 即可 |
| `rule` | 校验规则，见下表 |
| `type` | 字段类型，见下表 |
| `values` | `select` / `apps` 的选项列表，每项 `label` + `value` |
| `key` | `service` 类型依赖的应用 key，如 `mysql`、`redis` |
| `child` | `apps` 类型下嵌套的 `service` 字段 |

`type`：

| type | 用途 |
|---|---|
| `text` | 普通文本，明文显示 |
| `number` | 数字，端口必须用这个 |
| `password` | 密码、Token、密钥，默认掩码 |
| `select` | 下拉选项，配合 `values` |
| `service` | 依赖已安装的 1Panel 应用（配合 `key`），会联动注入 `PANEL_DB_HOST` 等 |
| `apps` | 先选依赖类型（如 MySQL / MariaDB），再通过 `child` 选具体实例 |

`rule`：

| rule | 规则 |
|---|---|
| `paramPort` | 1–65535 |
| `paramExtUrl` | `http(s)://域名或IP:端口` |
| `paramCommon` | 英文、数字、`.` `-` `_`，长度 2–30 |
| `paramComplexity` | 英文、数字、`.%@$!&~_-`，长度 6–30，特殊字符不能在首尾 |

端口约定：

1. 有 Web 访问端口时优先用 `PANEL_APP_PORT_HTTP`。
2. `envKey` 以 `PANEL_APP_PORT` 开头的字段会被当作端口，安装前做占用检查。填的是宿主机端口。
3. 其他端口用 `PANEL_APP_PORT_<后缀>`，如 `PANEL_APP_PORT_HTTPS`、`PANEL_APP_PORT_SOCKS`。
4. 端口字段统一 `type: number` + `rule: paramPort`。

变量对应：compose 里每个 `${VAR}` 都必须在本文件声明。例外是 1Panel 自动提供的变量，如 `${CONTAINER_NAME}`，以及 `service` 类型联动的 `PANEL_DB_*`、`PANEL_REDIS_*`。

---

## 4. `docker-compose.yml`

### 4.1 标准模板（bridge 网络）

```yaml
services:
  uptime-kuma:
    image: louislam/uptime-kuma:2.5.5
    container_name: ${CONTAINER_NAME}
    restart: always
    networks:
      - 1panel-network
    ports:
      - ${PANEL_APP_PORT_HTTP}:3001
    volumes:
      - ./data:/app/data
    labels:
      createdBy: "Apps"

networks:
  1panel-network:
    external: true
```

### 4.2 host 网络（仅在确有需要时）

代理、内网穿透这类需要监听宿主机端口或大量端口的应用可以用 host 网络，官方 `frps` 就是这样写的。host 模式下不能再写 `networks` 和 `ports`：

```yaml
services:
  frps:
    image: snowdreamtech/frps:0.71.0-alpine
    container_name: ${CONTAINER_NAME}
    restart: always
    network_mode: host
    volumes:
      - ./data/frps.toml:/etc/frp/frps.toml
    labels:
      createdBy: "Apps"
```

> 官方校验脚本对 host 模式会报 `compose must use 1panel-network`，这是误报。确认需要 host 网络时可以忽略，但要在 README 中写明。

### 4.3 硬性约定

| 规则 | 说明 |
|---|---|
| `container_name: ${CONTAINER_NAME}` | 主服务固定写法；其他服务用 `${CONTAINER_NAME}-<服务名>` |
| `restart: always` | 官方统一写法 |
| `networks: [1panel-network]` + `external: true` | 所有服务都加入（host 模式除外） |
| `labels.createdBy: "Apps"` | 所有服务都要有 |
| 端口用 `${PANEL_APP_PORT_*}` | 不要写死宿主机端口 |
| 持久化用相对路径 | `./data:/xxx`，不要写 `/opt/...` 绝对路径 |
| 镜像固定版本 | 不用 `:latest`，除非上游只发布 `latest` |
| 不写 `version:` | Compose v2 已废弃该字段 |

### 4.4 安全

- 不使用 `privileged: true`，除非应用必须。
- 不挂载 `/`、`/etc`、`/var/run/docker.sock` 等敏感路径，除非应用必须。
- 密码、Token 只通过表单 + 环境变量注入，不写进 compose 或镜像。
- 优先用上游官方镜像。用第三方镜像时在根 `data.yml` 的 `document` 或 README 中注明来源。

---

## 5. 生命周期脚本

位置：`<version>/scripts/`。没有需要就不建这个目录。

| 脚本 | 触发时机 | 超时 |
|---|---|---|
| `init.sh` | 安装时，容器启动前 | 10 分钟 |
| `upgrade.sh` | 升级时，旧容器停止、新脚本就位后，新容器启动前 | 10 分钟 |
| `uninstall.sh` | 卸载时，compose down 之后 | 10 分钟 |

执行规则：

- 在宿主机上执行 `bash <安装目录>/scripts/<hook>.sh`，工作目录是安装目录，所以 `./data`、`./.env` 都能直接用。
- 需要表单参数时显式 `source ./.env`（官方 `frps` 的 `init.sh` 就是这样做的）。
- 脚本非零退出会让对应操作失败。
- 修改参数不会重新执行 `init.sh`，只会重建容器。依赖参数的配置要在容器启动时生成，或在 `upgrade.sh` 中处理。
- `start.sh` / `stop.sh` / `restart.sh` 只在 1Panel 内部的生命周期脚本模式下生效，普通本地应用不要依赖。

编写要求：

- `#!/bin/bash`，LF 换行，`chmod 755`。
- 只操作安装目录内的相对路径。
- 可重复执行；失败时返回非零。
- `scripts/` 下可以放辅助文件（如 `entrypoint.sh`），1Panel 只会按上面三个文件名调用。
- 只做必要的事，例如非 root 容器需要的 `chown -R 1000:1000 ./data`。UID/GID 以上游 Dockerfile 为准。
- 不要放只有 `exit 0` 的空脚本。

```bash
#!/bin/bash
# init.sh：官方镜像以 UID 1000 运行（见上游 Dockerfile）
set -e
mkdir -p ./data
chown -R 1000:1000 ./data
```

---

## 6. README

只写给使用者看的内容，不写生成过程、调试记录、本地测试路径。

`README.md`：

```markdown
## 产品介绍

一两句话说明应用做什么。

## 主要功能

- 功能 1
- 功能 2
```

`README_en.md` 用 `## Introduction` / `## Features`。

可以补充默认端口、数据目录、首次使用步骤，保持简短。

---

## 7. 制作流程

1. 确认上游官方镜像、版本、端口、数据目录、运行用户、环境变量。
2. 定 `app-key` 和版本号，建目录骨架（1Panel 宿主机上也可以用 `1panel app init <key> <version>` 生成）。
3. 写根 `data.yml`、`README.md`、`README_en.md`、`logo.png`。
4. 写版本 `data.yml` 和 `docker-compose.yml`，变量一一对应。
5. 跑校验：

   ```bash
   git clone --depth 1 https://github.com/1Panel-dev/1Panel-appstore-skills.git /tmp/skills
   python3 /tmp/skills/scripts/validate_app_package.py apps/<app-key>
   bash -n apps/<app-key>/<version>/scripts/*.sh
   ```

6. 复制到 `/opt/1panel/resource/apps/local/`，应用商店点「更新应用列表」，在「本地」分类安装。
7. 测试：安装、启动、停止、重启、改参数、卸载、重装；有多个版本时测升级。确认端口、持久化数据、日志正常。

---

## 8. 同步、迁移与备份

同步到本机（见 [README.md](./README.md) 和 [scripts/sync-to-1panel.sh](./scripts/sync-to-1panel.sh)）：

```bash
cp -rf apps/* /opt/1panel/resource/apps/local/
```

`cp -rf` 只新增和覆盖。仓库里删除的应用，服务器上要手动删：

```bash
rm -rf /opt/1panel/resource/apps/local/<app-key>
```

安装后的实例目录：

```text
/opt/1panel/apps/<app-key>/<实例名>/
├── docker-compose.yml
├── .env            # 表单参数
├── data/           # 持久化数据
└── scripts/
```

备份分层：

| 层级 | 内容 | 方式 |
|---|---|---|
| 应用定义 | 本仓库 `apps/<app-key>/` | Git |
| 实例配置与数据 | 实例目录（`.env` + `data/`） | 优先用 1Panel 自带的应用备份；手动时先停应用再 `tar` |
| 镜像 | `docker save` | 仅离线环境需要 |

---

## 9. 验收清单

- [ ] `logo.png` 180×180，建议 ≤ 50 KB（画质自然无色带断层）
- [ ] 有 `README.md`，推荐有 `README_en.md`
- [ ] 根 `data.yml` 必填字段齐全，`description` 含 `en`、`zh`
- [ ] `key` 与目录名一致；版本目录无 `v` 前缀
- [ ] 版本 `data.yml` 有 `formFields`；compose 中所有自定义变量都已声明
- [ ] 端口用 `PANEL_APP_PORT_*` + `type: number` + `rule: paramPort`
- [ ] 密码、Token 用 `type: password`
- [ ] compose：`${CONTAINER_NAME}`、`restart: always`、`1panel-network`（external）、`createdBy: "Apps"`
- [ ] host 网络有明确理由并写进 README
- [ ] 镜像固定版本，不用 `:latest`
- [ ] 持久化用 `./` 相对路径；需要的目录带 `.gitkeep`
- [ ] 脚本只在需要时提供，`bash -n` 通过，可执行权限 755
- [ ] 官方校验脚本通过（可忽略：host 模式的网络误报、description 缺少其他语言）
- [ ] 本地商店刷新后能安装、改参数；重启后数据保留；卸载前备份，重装后可恢复数据
