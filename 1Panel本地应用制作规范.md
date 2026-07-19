# 1Panel 本地应用制作规范（简化版）

> **文档目的**：按官方兼容格式封装 Docker 应用，便于**整包移植**、**备份恢复**、在多台 1Panel 主机间复用。  
> **适用范围**：本地应用商店（`/opt/1panel/resource/apps/local`），不强制上架官方商店。  
> **依据来源**：
> - [1Panel 文档 · 应用商店](https://1panel.cn/docs/v1/user_manual/appstore/appstore/)
> - [官方 appstore 仓库](https://github.com/1Panel-dev/appstore)
> - [1Panel-appstore-skills 格式说明](https://github.com/1Panel-dev/1Panel-appstore-skills)
> - [社区教程：自助创建 1Panel 应用](https://bbs.fit2cloud.com/t/topic/7409)
> - [社区教程：本地应用创建技巧](https://bbs.fit2cloud.com/t/topic/640)

---

## 1. 一句话理解

把任意可 Docker 部署的服务，整理成 **固定目录结构 + `data.yml` 声明 + `docker-compose.yml`**，丢进 1Panel 的 `local` 目录后，就能在应用商店里一键安装、升级、备份、卸载。

**本地生效路径（默认安装）：**

```text
/opt/1panel/resource/apps/local/<app-key>/
```

> 若 1Panel 未装在 `/opt`，按实际安装根目录替换。

刷新方式：应用商店 → **更新应用列表 / 刷新本地应用**。

---

## 2. 标准目录结构（必遵循）

```text
<app-key>/
├── logo.png                 # 应用图标，建议 180×180
├── README.md                # 中文说明（产品介绍）
├── README_en.md             # 英文说明（可选，但推荐）
├── data.yml                 # 应用元数据（名称、标签、类型等）
└── <version>/               # 版本目录，如 1.0.0（不要以 v 开头）
    ├── data.yml             # 安装表单（环境变量）
    ├── docker-compose.yml   # 编排文件
    ├── data/                # 持久化目录模板（可含 .gitkeep）
    └── scripts/             # 可选生命周期脚本
        ├── init.sh          # 安装前
        ├── upgrade.sh       # 升级前
        └── uninstall.sh     # 卸载后
```

### 命名规则

| 项 | 规则 | 示例 |
|---|---|---|
| `app-key` | 英文小写 + 数字 + 短横线，作文件夹名 | `embyproxy` |
| 版本号 | 语义化版本，**不要** `v` 前缀 | `1.0.0`、`2.3.1` |
| 升级判定 | 1Panel 按**版本目录名**比较是否有更新 | 新增 `1.0.1/` 即视为新版本 |

### 本仓库示例

当前工作区中的 `embyproxy/` 即按此结构组织，可直接作为模板参考。

---

## 3. 根目录 `data.yml`（应用声明）

声明应用身份与展示信息。

### 3.1 最小可用（本地优先，够用即可）

```yaml
name: EmbyProxy
tags:
  - Media
title: EmbyProxy
description: EmbyProxy Docker Application

additionalProperties:
  key: embyproxy
  name: EmbyProxy
  tags:
    - Tool          # 或 WebSite / Database / Media 等
  shortDescZh: Emby代理服务
  shortDescEn: EmbyProxy
  type: tool        # website | runtime | tool
  crossVersionUpdate: true
  limit: 0          # 0 = 不限安装次数
  website: https://example.com
  github: https://github.com/example/app
  document: https://example.com/docs
  architectures:
    - amd64
    - arm64
```

### 3.2 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `additionalProperties.key` | 是 | 应用唯一 key，与文件夹名一致 |
| `name` / `additionalProperties.name` | 是 | 显示名称 |
| `tags` | 是 | 分类标签，如 `Tool`、`WebSite`、`Database`、`Runtime`、`Server`、`CI/CD`、`Local` |
| `shortDescZh` / `shortDescEn` | 推荐 | 短描述，中文建议 ≤ 30 字 |
| `type` | 推荐 | `website` 可一键挂网站；`runtime` 运行时/中间件；`tool` 工具类 |
| `crossVersionUpdate` | 推荐 | 是否允许跨大版本升级 |
| `limit` | 推荐 | 最大安装实例数，`0` 不限 |
| `website` / `github` / `document` | 推荐 | 外链，便于运维定位来源 |
| `architectures` | 推荐 | 如 `amd64`、`arm64`，避免装到错误架构 |
| `description` 多语言 | 可选 | 官方商店更全；本地可只做中英 |

### 3.3 `type` 选择建议

| type | 适用场景 |
|---|---|
| `website` | 有 Web UI、希望从「网站」一键部署的应用（WordPress、Halo、FileBrowser） |
| `runtime` | 数据库、反向代理、缓存等基础设施（MySQL、Redis、OpenResty） |
| `tool` | 运维工具、代理、面板辅助服务（Jenkins、phpMyAdmin、本仓库的 EmbyProxy） |

---

## 4. 版本目录 `data.yml`（安装表单）

控制安装/编辑时用户填写的参数，值会注入 `docker-compose.yml` 的 `${ENV}`。

### 4.1 示例

```yaml
additionalProperties:
  formFields:
    - default: 8787
      edit: true
      envKey: PANEL_APP_PORT_HTTP
      labelZh: 端口
      labelEn: Port
      required: true
      rule: paramPort
      type: number

    - default: change-this-token
      edit: true
      envKey: ADMIN_TOKEN
      labelZh: 管理Token
      labelEn: Admin Token
      required: true
      type: password
      random: true          # 可选：默认值后追加随机串

    - default: Asia/Shanghai
      edit: true
      envKey: TZ
      labelZh: 时区
      labelEn: Timezone
      required: true
      type: text
```

### 4.2 表单 `type`

| type | 用途 |
|---|---|
| `text` | 普通文本 |
| `number` | 数字（端口等） |
| `password` | 密钥/密码（界面默认掩码） |
| `select` | 下拉选项（配合 `values`） |
| `service` | 依赖已安装的 1Panel 应用（如 MySQL），配合 `key: mysql` |

### 4.3 校验 `rule`

| rule | 含义 |
|---|---|
| `paramPort` | 端口 1–65535 |
| `paramExtUrl` | `http(s)://域名或IP:端口` |
| `paramCommon` | 英文数字 `._-`，长度 2–30 |
| `paramComplexity` | 密码复杂度（长度 6–30 等） |

### 4.4 端口约定（重要）

1. 有 Web 访问端口时，优先使用 **`PANEL_APP_PORT_HTTP`**。
2. 凡 `envKey` 含 **`PANEL_APP_PORT`** 前缀，会被当作端口做占用检查（填的是**宿主机端口**）。
3. 其他端口可用：`PANEL_APP_PORT_HTTPS`、`PANEL_APP_PORT_TCP` 等自定义后缀。

### 4.5 变量对应原则

- `docker-compose.yml` 中每个自定义 `${VAR}`，必须在版本 `data.yml` 的 `formFields.envKey` 中声明。
- **例外**（1Panel 内置，无需表单声明）：
  - `${CONTAINER_NAME}`
  - 部分服务联动变量如 `${PANEL_DB_PORT}`（依赖 service 类型时）

---

## 5. `docker-compose.yml` 规范

### 5.1 推荐模板（单服务）

```yaml
services:
  embyproxy:
    image: ghcr.io/example/embyproxy:1.0.0
    container_name: ${CONTAINER_NAME}
    restart: unless-stopped
    networks:
      - 1panel-network
    ports:
      - ${PANEL_APP_PORT_HTTP}:8787
    volumes:
      - ./data:/app/data
    environment:
      ADMIN_TOKEN: ${ADMIN_TOKEN}
      TZ: ${TZ}
    labels:
      createdBy: Apps

networks:
  1panel-network:
    external: true
```

### 5.2 硬性约定

| 规则 | 说明 |
|---|---|
| `container_name: ${CONTAINER_NAME}` | 主服务固定写法；从服务用 `${CONTAINER_NAME}-xxx` |
| 加入 `1panel-network` | 与商店其他应用互通 |
| `1panel-network: external: true` | 使用 1Panel 预创建的外部网络 |
| `labels.createdBy: Apps` | 标记为应用商店创建 |
| 数据卷用**相对路径** | 如 `./data:/app/data`，便于备份与移植 |
| 镜像尽量钉版本 | 生产避免长期依赖 `:latest`（本地测试可放宽） |

### 5.3 持久化与备份友好设计

为便于**移植备份**，请遵守：

1. **所有业务数据只落在应用目录相对路径**（`./data`、`./config`、`./logs`），不要写死 `/opt/...` 绝对路径。
2. 配置文件、SQLite、上传文件等统一放在挂载卷内。
3. 密钥通过 `formFields` + 环境变量注入，**不要**硬编码进镜像或 compose。
4. 安装后运行目录通常类似：
   ```text
   /opt/1panel/apps/<app-key>/<实例名>/
   ```
   备份时连同 `data/`、`.env`（若有）、compose 一并打包即可迁移。

---

## 6. 生命周期脚本（可选）

路径：`<version>/scripts/`

| 脚本 | 触发时机 | 常见用途 |
|---|---|---|
| `init.sh` | 安装前 | 创建目录、`chown` 权限（非 root 容器） |
| `upgrade.sh` | 升级前 | 数据迁移、兼容处理 |
| `uninstall.sh` | 卸载后 | 清理残留（谨慎删除数据） |

```bash
#!/bin/bash
# init.sh 示例
mkdir -p ./data
# 若官方镜像以 UID 1000 运行：
# chown -R 1000:1000 ./data
```

**原则**：没有初始化必要就不建 `scripts/`；UID/GID 以官方 Dockerfile/文档为准，不要臆造。

---

## 7. README 编写

简洁即可，不要写生成过程、调试记录。

**中文 `README.md`：**

```markdown
## 产品介绍

简要说明本应用做什么。

## 主要功能

- 功能 1
- 功能 2

## 默认端口

8787

## 数据目录

`./data`
```

**英文 `README_en.md`：** 使用 `## Introduction` / `## Features`。

---

## 8. 制作流程（推荐 5 步）

```text
1. 确认官方 Docker 镜像 / compose / 端口 / 数据目录 / 环境变量
2. 选定 app-key 与 version，创建目录骨架
3. 写根 data.yml + README + logo
4. 写版本 data.yml（表单）与 docker-compose.yml（变量一一对应）
5. 拷贝到 local 目录 → 刷新商店 → 安装验证
```

### 快速初始化命令（宿主机有 1Panel CLI 时）

```bash
1panel app help
1panel app init -k <app-key> -v <version>
# 例：1panel app init -k embyproxy -v 1.0.0
```

---

## 9. 本地安装 / 移植 / 备份

### 9.1 首次上架到本机

```bash
# 将制作好的应用包放到 local
cp -r ./embyproxy /opt/1panel/resource/apps/local/

# 权限（按实际用户调整）
chown -R root:root /opt/1panel/resource/apps/local/embyproxy
```

然后：1Panel → 应用商店 → **更新应用列表** → 在「本地」分类安装。

### 9.2 应用包移植（定义 → 另一台机器）

只需拷贝**定义包**（商店模板）：

```bash
# 源机
tar czf embyproxy-appdef.tar.gz -C /opt/1panel/resource/apps/local embyproxy

# 目标机
tar xzf embyproxy-appdef.tar.gz -C /opt/1panel/resource/apps/local
# 刷新应用列表后安装
```

### 9.3 运行实例备份（数据 + 配置）

安装后的实例目录（路径可能因版本略有差异，以实际为准）：

```text
/opt/1panel/apps/<app-key>/<name>/
  ├── docker-compose.yml
  ├── .env                 # 安装参数
  └── data/                # 持久化数据
```

备份示例：

```bash
# 停应用更安全（可在 1Panel UI 操作）
INSTANCE_DIR=/opt/1panel/apps/embyproxy/<实例名>
tar czf embyproxy-backup-$(date +%F).tar.gz -C "$INSTANCE_DIR" .
```

恢复示例：

```bash
# 目标机先用「应用定义」安装一次同名/同端口应用，或手动放置 compose+.env
tar xzf embyproxy-backup-xxxx.tar.gz -C /opt/1panel/apps/embyproxy/<实例名>
# 再在 1Panel 中启动 / docker compose up -d
```

### 9.4 备份分层建议

| 层级 | 内容 | 何时备份 |
|---|---|---|
| **定义包** | `local/<app-key>/` | 制作完成、版本变更后 |
| **实例配置** | `.env`、compose | 改端口/密钥后 |
| **业务数据** | `./data` 等卷 | 按业务频率（日/周） |
| **镜像** | `docker save` | 内网离线或源站不稳时 |

---

## 10. 验收清单（交付前自检）

- [ ] 目录：`logo.png`、`README.md`、根 `data.yml`、`<version>/data.yml`、`docker-compose.yml`
- [ ] `key` 与文件夹名一致
- [ ] 版本号无 `v` 前缀
- [ ] compose 使用 `${CONTAINER_NAME}` 与 `1panel-network`
- [ ] 所有自定义 `${VAR}` 已在版本 `data.yml` 声明
- [ ] Web 端口使用 `PANEL_APP_PORT_HTTP` + `rule: paramPort`
- [ ] 数据卷为相对路径 `./...`
- [ ] 敏感项使用 `type: password`
- [ ] 在 `local` 刷新后可出现并成功安装
- [ ] 安装后数据写入挂载目录，卸载重装可恢复（备份场景）

---

## 11. 与本仓库的关系

```text
1panel-app/
├── 1Panel本地应用制作规范.md   ← 本文档
└── embyproxy/                  ← 本地应用示例
    ├── data.yml
    ├── logo.png
    ├── README.md
    └── 1.0.0/
        ├── data.yml
        ├── docker-compose.yml
        ├── data/
        └── scripts/
```

后续新增应用：复制 `embyproxy` 骨架改 key/镜像/表单即可；遵守本文规范即可在多台 1Panel 间稳定移植与备份。

---

## 12. 参考链接

| 资源 | 链接 |
|---|---|
| 1Panel 应用商店说明 | https://1panel.cn/docs/v1/user_manual/appstore/appstore/ |
| 官方应用仓库 | https://github.com/1Panel-dev/appstore |
| 提交/自定义应用 Wiki | https://github.com/1Panel-dev/appstore/wiki |
| 官方封装 Skill | https://github.com/1Panel-dev/1Panel-appstore-skills |
| 社区：本地应用技巧 | https://bbs.fit2cloud.com/t/topic/640 |
| 社区：自助创建应用 | https://bbs.fit2cloud.com/t/topic/7409 |

---

*文档版本：1.0 · 面向本地简化封装与迁移备份 · 非官方商店上架审核全文*
