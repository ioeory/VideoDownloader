# 📹 VideoDownloader

**通用视频下载器** — 一站式下载 YouTube、Bilibili、Vimeo、Coursera、Harvard CS50、DeepLearning.AI、KodeKloud、Skills Google 等平台的视频课程。

支持 **CLI 命令行** 与 **深色主题 GUI 图形界面** 双模式，具备播放列表批量下载、画质选择 (4K/1080p/720p)、断点续传、Cookie 鉴权、中英双语界面等功能，基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 引擎。

---

## ✨ 特性一览

| 特性 | 说明 |
|------|------|
| 🎬 **多平台支持** | YouTube / Bilibili / Vimeo / Coursera / Harvard CS50 / DeepLearning.AI / KodeKloud / Skills Google + 任意 yt-dlp 支持站点 |
| 🖥️ **GUI 图形界面** | 基于 CustomTkinter 的深色现代主题，集成实时进度条、日志动态输出、暂停/停止控制 |
| 🌐 **中英双语 (i18n)** | GUI 界面与日志输出均支持中英文实时切换 |
| 📦 **播放列表批量下载** | 自动创建以列表名命名的子目录，支持 `--playlist-items` 范围切片 |
| 🎯 **画质选择** | 4K / 1080p Premium / 1080p / 720p / 480p / 纯音频 |
| 🔄 **断点续传** | 中断后重新运行自动从上次位置继续，已下载文件自动跳过 |
| 🍪 **灵活鉴权** | cookies.txt 文件 / 浏览器自动提取 (含 WSL DPAPI 解密) / 手动粘贴 / 剪贴板导入 |
| ⚡ **并发下载** | 支持 1-5 线程并发，适用于大批量课程下载 |
| 🛡️ **YouTube 反爬对抗** | 自动启用多 Player Client 轮询 + Node.js EJS solver |
| ⏭️ **容错跳过** | 播放列表中遇到不可用视频自动跳过，不中断整体下载 |
| 🔌 **插件架构** | 实现 `BasePlugin` 接口即可扩展新平台 |
| 🖥️ **跨平台** | Linux / macOS / Windows (含 WSL) |
| 📝 **详细日志** | 下载日志包含完整文件名与源 URL，方便失败重下 |

---

## ⚡ 快速安装

### 方式一：pip 安装（推荐）

```bash
git clone https://github.com/your-username/VideoDownloader.git
cd VideoDownloader
pip install -e .

# 验证 CLI
vd -h

# 启动 GUI
vd-gui
```

### 方式二：Windows 一键安装

双击运行 `install.bat`，自动完成：
1. Python 3.12 检测与安装
2. VideoDownloader 包与所有依赖安装
3. ffmpeg 下载与 PATH 配置
4. Node.js 检测提示
5. 桌面快捷方式创建

### 方式三：传统方式

```bash
pip install -r requirements.txt
python main.py -h
```

### 系统要求

| 依赖 | 用途 | 必需 |
|------|------|------|
| **Python** ≥ 3.10 | 运行环境 | ✅ |
| **ffmpeg** | 合并音视频轨（yt-dlp 需要） | ✅ |
| **Node.js** | Cookie 模式下解密 YouTube JS 签名 | 可选 |
| **python3-tk** | Linux/WSL 下运行 GUI | GUI 模式 |

---

## 🖥️ GUI 图形界面

```bash
# pip 安装后，全局任意终端启动：
vd-gui

# 或直接运行：
python videodownloader/gui/app.py
```

### GUI 功能

- **平台选择** — 下拉切换 Generic / Harvard / DeepLearning.AI / Coursera / KodeKloud / Skills Google
- **画质/并发/字幕** — 根据平台动态显示配置选项
- **Cookie 管理** — 支持无鉴权 / Chrome / Edge / Firefox / Brave 浏览器提取 / 文件导入 / 剪贴板粘贴
- **实时日志** — 左侧日志区带颜色高亮 (ERROR=红 / WARNING=橙 / INFO=白 / DEBUG=灰)
- **进度控制** — 实时进度条 + 暂停/继续/停止控制
- **配置持久化** — 关闭时自动保存所有配置，下次启动自动恢复
- **语言切换** — 一键切换中文/英文界面
- **统一深色主题弹窗** — 所有对话框均跟随主程序深色色系

---

## 🚀 CLI 使用示例

> 安装后可用 `vd` 代替 `python main.py`，两者等价。

### 通用下载（YouTube / Bilibili / Vimeo 等）

```bash
# 下载公开视频
vd download "https://www.youtube.com/watch?v=jNQXAC9IVRw"

# 指定画质
vd download "https://www.youtube.com/watch?v=xxx" -q 1080p

# 4K 超清下载（需 Cookie 认证）
vd download "https://www.youtube.com/watch?v=xxx" -q 4k --cookies-file cookies.txt

# 下载播放列表（仅前 25 个视频）
vd download "https://www.youtube.com/watch?v=xxx&list=PLxxx" --playlist-items 1-25

# 仅下载音频
vd download "https://www.youtube.com/watch?v=xxx" -q audio

# 下载字幕 + 2 并发
vd download "https://www.youtube.com/watch?v=xxx" --subtitle -c 2
```

### Harvard CS50 课程

自动提取全部章节的 YouTube 视频、PDF 讲义、ZIP 源码包，按周归档。

```bash
vd harvard --url "https://cs50.harvard.edu/python/"
vd harvard --url "https://cs50.harvard.edu/x/" --quality 1080p
```

### DeepLearning.AI 课程

```bash
# 查看内置支持的课程
vd list-courses

# 下载全部（需 Cookie）
vd deeplearning --course ai-for-everyone --cookies-file cookies.txt

# 仅下载 Week 1 和 Week 2
vd deeplearning --course ai-for-everyone --weeks 1 2 --cookies-file cookies.txt
```

### Coursera / KodeKloud / Skills Google

```bash
# Coursera
vd coursera --url "https://www.coursera.org/learn/..." --cookies-file cookies.txt

# KodeKloud（支持课程页和单课时页 URL）
vd kodekloud --url "https://learn.kodekloud.com/user/courses/..." --cookies-file cookies.txt

# Skills Google
vd skillsgoogle --url "https://www.skills.google/paths/..." --cookies-file cookies.txt
```

---

## 📋 全部参数

### 通用参数（所有子命令共享）

| 参数 | 说明 | 默认 |
|------|------|------|
| `-o, --output-dir` | 输出目录 | `./downloads` |
| `-c, --concurrent` | 并发下载数（建议 ≤ 3） | `1` |
| `--cookies-file FILE` | Netscape 格式 cookies.txt | - |
| `--cookie STRING` | 手动 Cookie 字符串 | - |
| `-b, --browser` | 从浏览器提取 Cookie | `chrome` |
| `-v, --verbose` | 调试日志 | 否 |

### `download` 专属参数

| 参数 | 说明 | 默认 |
|------|------|------|
| `-q, --quality` | `best` / `4k` / `1080p` / `720p` / `480p` / `audio` | `best` |
| `--subtitle` | 下载字幕 | 否 |
| `--playlist-items` | 播放列表范围（如 `1-25`, `1,3,5-7`） | 全部 |

---

## 🔑 Cookie 获取方法

| 方法 | 适用场景 |
|------|----------|
| `--cookies-file cookies.txt` | **WSL 推荐**，通过「Get cookies.txt LOCALLY」扩展导出 |
| `-b chrome` | 非 WSL 本机环境，自动从浏览器直接提取 |
| `--cookie "key=val; ..."` | 手动粘贴（DevTools → Application → Cookies） |
| GUI 剪贴板模式 | 在 GUI 中选择"剪贴板"，直接粘贴 Cookie 字符串 |

> **WSL 用户**：安装 Chrome 扩展 [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)，访问目标网站后导出 `cookies.txt`。WSL 环境下还支持通过 DPAPI 直接解密 Windows 浏览器 Cookie 数据库。

> **提示**：下载公开视频（YouTube 免登录视频）时**无需** Cookie，省去 Cookie 参数反而更快。

---

## 🏗️ 项目架构

```
VideoDownloader/
├── pyproject.toml                  # 包配置 & CLI/GUI 入口点定义
├── install.bat                     # Windows 一键安装脚本（含桌面快捷方式）
├── requirements.txt                # 传统依赖清单
├── config.example.yaml             # YAML 配置参考
├── main.py                         # 传统入口（python main.py）
├── rebuild_i18n.py                 # i18n 翻译字典重建工具
├── build_exe.py                    # PyInstaller 打包脚本
│
├── videodownloader/                # Python 包主体
│   ├── __init__.py                 # 版本号 (v1.0.0)
│   ├── main.py                     # CLI 主程序（argparse + 子命令）
│   │
│   ├── core/                       # 核心引擎
│   │   ├── cookies.py              # Cookie 管理（Netscape 文件 / 浏览器提取 / WSL DPAPI 解密）
│   │   ├── downloader.py           # 下载引擎（yt-dlp + requests 双引擎 + 断点续传）
│   │   └── utils.py                # 工具函数（日志配置 / WSL 检测）
│   │
│   ├── plugins/                    # 平台插件
│   │   ├── base.py                 # 插件抽象基类（BasePlugin）
│   │   ├── generic_ytdlp.py        # 通用 yt-dlp（YouTube/Bilibili/Vimeo 等）
│   │   ├── harvard.py              # Harvard CS50（视频 + PDF + ZIP，按周归档）
│   │   ├── deeplearning_ai.py      # DeepLearning.AI（API 解析 + m3u8）
│   │   ├── coursera.py             # Coursera（API 解析）
│   │   ├── kodekloud.py            # KodeKloud（课程/单课时 URL 解析）
│   │   └── skills_google.py        # Skills Google（路径解析）
│   │
│   └── gui/                        # GUI 图形界面
│       └── app.py                  # CustomTkinter 深色主题 GUI（~1400行）
│
├── docs/                           # 技术文档
│   ├── architecture.md             # 系统架构
│   ├── plugins.md                  # 插件开发指南
│   ├── i18n.md                     # 国际化流程
│   ├── config.md                   # 配置手册
│   └── development.md              # 开发与构建
│
└── core/ & plugins/                # 传统路径（向后兼容 python main.py）
```

### 核心模块说明

| 模块 | 职责 |
|------|------|
| `core/downloader.py` | 双引擎下载：yt-dlp 处理复杂源（m3u8/DASH/YouTube），requests 处理纯 MP4 直链。`DownloadTask` 数据类封装 URL/文件名/Cookie/元数据 |
| `core/cookies.py` | 统一 Cookie 管理器 `CookieManager`：优先级 cookies_file > cookie_str > 浏览器提取。WSL 模式下通过 PowerShell 调用 DPAPI 解密 |
| `plugins/base.py` | 抽象基类 `BasePlugin`，定义 `get_download_tasks()` / `can_handle()` / `get_cookies_domain()` 接口 |
| `gui/app.py` | 基于 CustomTkinter 的完整 GUI，含 i18n 字典、配置持久化、yt-dlp 进度回调、自定义深色主题弹窗 |

---

## 📁 下载目录结构

```
downloads/
├── Norway 4K • Scenic Relaxation.mp4              # 通用单视频
├── Mix - Playlist Title/                           # YouTube 播放列表
│   ├── 001 - Video Title 1.mp4
│   ├── 002 - Video Title 2.mp4
│   └── ...
├── CS50's Introduction to Programming/             # Harvard 课程（按周归档）
│   ├── 00 - Functions, Variables/
│   │   ├── 00 - Video_1.mp4
│   │   ├── Resource - lecture0.pdf
│   │   └── Resource - src0.zip
│   └── 01 - Conditionals/
│       └── ...
├── ai-for-everyone/                                # DeepLearning.AI 课程
│   ├── Week_01/
│   │   ├── 01_Introduction.mp4
│   │   └── ...
│   └── Week_02/
│       └── ...
└── kodekloud-course-name/                          # KodeKloud 课程
    ├── 01 - Module Name - Lesson 1.mp4
    └── ...
```

---

## 🔧 维护与升级

```bash
# YouTube 接口变化时，升级 yt-dlp 即可修复
pip install --upgrade yt-dlp

# 升级 VideoDownloader 本身
cd VideoDownloader && pip install -e .

# 重建 i18n 翻译（修改翻译字典后）
python rebuild_i18n.py

# 打包为 Windows 独立 exe
python build_exe.py
```

---

## ⚙️ 配置文件

支持 `config.yaml` 自定义默认参数（复制 `config.example.yaml` 为 `config.yaml`）：

```yaml
output_dir: ./downloads      # 默认输出目录
concurrent: 1                # 默认并发数
browser: chrome              # 默认浏览器（Cookie 提取）
quality: best                # 默认画质
log_file: download.log       # 日志文件路径

deeplearning:
  # default_course: ai-for-everyone
  # weeks: [1, 2]
```

GUI 模式下配置自动保存在 `~/.videodownloader_gui.json`，包含平台/画质/Cookie/语言等所有选项。

---

## 📖 技术文档

| 文档 | 内容 |
|------|------|
| [🏗️ 系统架构](docs/architecture.md) | 模块化设计、数据流、CLI/GUI 双前端 |
| [🔌 插件开发](docs/plugins.md) | BasePlugin 接口、如何支持新网站 |
| [🌐 国际化流程](docs/i18n.md) | Patch-based 翻译机制、rebuild_i18n.py 使用 |
| [⚙️ 配置手册](docs/config.md) | config.yaml 高级参数说明 |
| [🛠️ 开发与构建](docs/development.md) | 测试、PyInstaller 编译与发布 |

---

## ⚠️ 注意事项

- 本工具仅供**个人学习**使用，请遵守各平台服务条款
- 需要登录的内容必须提供有效 Cookie
- 并发数建议不超过 3，过高可能被平台限速
- 日志保存在 `download.log`，包含完整文件名与源 URL
- WSL 下运行 GUI 需确保安装 `python3-tk` 并配置 X Server

## 📄 License

MIT
