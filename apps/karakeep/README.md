## 产品介绍

Karakeep（前称 Hoarder）是自托管书签 / 稍后读应用，支持链接抓取归档、全文搜索，并可选用 AI 自动打标。

本应用按官方 Docker Compose 封装：**不依赖 PostgreSQL**，业务数据使用内置 **SQLite**，搜索使用随包启动的 Meilisearch，抓取使用无头 Chrome。

## 主要功能

- 书签 / 稍后读、页面快照与归档
- Meilisearch 全文搜索（随应用一起部署）
- 可选 OpenAI 自动打标（安装时可填 API Key，也可装后再改环境变量）
- 浏览器扩展与移动端配套（见官方文档）

## 组件说明

| 服务 | 作用 |
|---|---|
| web | Karakeep 主应用（容器内 3000） |
| chrome | 无头浏览器，用于页面渲染与截图 |
| meilisearch | 全文搜索索引 |

## 默认端口

| 用途 | 默认宿主机端口 | 容器端口 |
|---|---|---|
| Web | 3000 | 3000（固定） |

安装时请把 **访问地址（NEXTAUTH_URL）** 改成实际访问入口，例如：

- `http://192.168.1.10:3000`
- `https://karakeep.example.com`（反代 HTTPS 时用域名）

## 数据目录

| 路径 | 内容 |
|---|---|
| `./data` | SQLite 数据库、抓取资源等 |
| `./meili_data` | Meilisearch 索引数据 |

备份时请同时备份这两个目录与实例 `.env`。

## 关于数据库

- **不需要** 1Panel 的 PostgreSQL / MySQL
- 主库为 **SQLite**（`DATA_DIR=/data`）
- 推荐开启 **SQLite WAL**（默认已开）

## 安装注意

1. 首次打开会进入注册页；若只给自己用，装好后可把「禁止新用户注册」改为 true 后重建/更新参数。
2. `NEXTAUTH_SECRET`、`MEILI_MASTER_KEY` 安装时建议使用随机值，**不要**与示例相同。
3. OpenAI Key 非必填；不填也能用，只是没有 AI 自动打标。
4. Chrome 镜像体积较大，首次拉取可能较慢。
