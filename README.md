# 1Panel 第三方本地应用商店

精选、高质量、开箱即用的 1Panel 本地扩展应用市场。遵循官方规范，支持数据持久化与一键同步。

[English](./README_en.md) · [应用制作规范](./1Panel本地应用制作规范.md)

---

## 📖 项目简介

本项目旨在为 **[1Panel](https://1panel.cn/)** 用户提供官方商店之外的扩展应用资源库。所有应用均遵循官方标准目录格式，针对个人服务器、轻量 VPS 做了深度优化（如开箱即用的数据持久化、自动权限处理、精简依赖），让你可以像使用官方商店一样一键安装、更新、配置和备份。

---

## 🚀 快速使用

### 方式一：一行命令一键同步（推荐）

在你的 1Panel 服务器终端中直接执行以下命令，即可全自动同步所有应用：

```bash
curl -sSL https://raw.githubusercontent.com/mainsir/1panel-apps/main/scripts/sync-to-1panel.sh | bash
```

> **提示**：如果无法直连 GitHub，可通过镜像代理加速：
> ```bash
> curl -sSL https://ghproxy.net/https://raw.githubusercontent.com/mainsir/1panel-apps/main/scripts/sync-to-1panel.sh | bash
> ```

---

### 方式二：1Panel 计划任务自动更新（推荐长期使用）

通过 1Panel 后台定时任务，每天自动拉取最新应用包，永不落后：

1. 打开 1Panel 后台 → **计划任务** → **创建任务**
2. 任务名称填写：`同步第三方本地应用`
3. 执行周期选择：`每天`（例如 `03:00`）
4. 任务类型选择：`Shell 脚本`
5. 脚本内容粘贴：
   ```bash
   curl -sSL https://raw.githubusercontent.com/mainsir/1panel-apps/main/scripts/sync-to-1panel.sh | bash
   ```
6. 点击确定保存即可。

---

### 方式三：手动 Git 克隆

```bash
# 克隆仓库到服务器
git clone https://github.com/mainsir/1panel-apps.git /opt/1panel-apps

# 创建 1Panel 本地应用目录并同步
mkdir -p /opt/1panel/resource/apps/local
cp -rf /opt/1panel-apps/apps/* /opt/1panel/resource/apps/local/
```

---

## 🖥️ 在 1Panel 中安装应用（3 步完成）

执行同步成功后，按照以下三步即可在面板中使用：

```
[第 1 步 执行同步] ──► [第 2 步 点击“更新应用列表”] ──► [第 3 步 切换到“本地”分类安装]
```

1. **进入应用商店**：登录 1Panel 面板，点击左侧菜单 **「应用商店」**。
2. **刷新本地应用**：点击页面右上角的 **「更新应用列表」** 按钮，面板将重新索引本地文件。
3. **一键安装**：在左侧分类导航中点击 **「本地」**，找到所需应用，点击 **「安装」**，填写表单参数（端口、密码等）后确认部署！

> [!TIP]
> 如果后续删除了本仓库中的某个应用，可手动在服务器清理已同步的本地目录：  
> `rm -rf /opt/1panel/resource/apps/local/<app-key>`

---

## 📦 已收录应用列表

| 图标 | 应用 Key | 应用名称 | 分类 | 架构 | 特性说明 |
|:---:|:---|:---|:---:|:---:|:---|
| <img src="./apps/3proxy/logo.png" width="40"/> | [3proxy](./apps/3proxy) | **3proxy** | 工具 | amd64 / arm64 | 极轻量 HTTP / SOCKS5 双协议代理服务器，基于环境变量快速部署 |
| <img src="./apps/gitea-sqlite/logo.png" width="40"/> | [gitea-sqlite](./apps/gitea-sqlite) | **Gitea SQLite版** | 开发/运维 | amd64 / arm64 | 单容器轻量 Git 托管，内置 SQLite3，免安装 MySQL，1C1G 小内存也能流畅运行 |
| <img src="./apps/kasmweb-chrome/logo.png" width="40"/> | [kasmweb-chrome](./apps/kasmweb-chrome) | **Kasm Chrome** | 工具 | amd64 | Web 端 60fps 高清流畅 Chrome 浏览器，支持 WebRTC 声音播放、剪贴板及全量书签持久化 |
| <img src="./apps/sing-box-reality/logo.png" width="40"/> | [sing-box-reality](./apps/sing-box-reality) | **VLESS Reality** | 工具 | amd64 | 基于 sing-box 的轻量 VLESS Reality 快速入站部署，自动生成密钥与分享链接 |

---

## 🛠️ 应用制作与规范

如果你想向本项目贡献新的应用，或者制作自己的私有应用包，请严格查阅我们的制作规范文档：

👉 **[1Panel 本地应用制作规范 (详细指南)](./1Panel本地应用制作规范.md)**

### 核心规范要点：
* **结构完整**：根目录包含 `logo.png`（180×180，≤15 KB）、`README.md`、`data.yml`，版本目录包含 `data.yml`、`docker-compose.yml`。
* **语言精简**：仅需提供中文（`zh`）与英文（`en`），避免繁冗小语种。
* **数据持久化**：统一使用 `./data` 相对路径挂载，非 root 容器配齐 `init.sh` 权限初始化。
* **规范命名**：网络统一使用 `1panel-network`（除非 host 网络），标签 `labels.createdBy: "Apps"`。

---

## 🤝 参与贡献

我们非常欢迎社区开发者提交新的应用包或改进现有配置！

1. **Fork** 本仓库
2. 创建特性分支：`git checkout -b app/my-cool-app`
3. 按照规范在 `apps/` 目录下添加你的应用包
4. 本地自测无误后提交代码并推送到你的分支
5. 提交 **Pull Request**，项目的 GitHub Actions 自动化流水线将自动运行语法与包结构验证

---

## 📄 License

本项目采用 [MIT License](LICENSE) 开源协议。
各应用镜像由其原作者或官方组织维护，请遵循各自软件的开源协议与使用规范。
