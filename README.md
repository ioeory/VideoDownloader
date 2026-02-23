# 📹 VideoDownloader

**通用视频下载器** — 一键下载 YouTube、Bilibili、Vimeo、Coursera、Harvard CS50、DeepLearning.AI、KodeKloud 等平台的视频课程。

支持**播放列表批量下载**、**画质选择 (4K/1080p/720p)**、**断点续传**、**Cookie 鉴权**，基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 引擎。

---

## ⚡ 快速安装

### 方式一：pip 安装（推荐）

```bash
# 克隆仓库
git clone https://github.com/your-username/VideoDownloader.git
cd VideoDownloader

# 安装为全局 CLI 工具
pip install -e .

# 验证
vd -h
```

### 方式二：Windows 一键安装

双击运行 `install.bat`，自动完成 Python + ffmpeg + 依赖安装。

### 方式三：传统方式

```bash
pip install -r requirements.txt
python main.py -h
```

---

## 🖥️ 图形交互界面 (GUI) 🌟全新上线🌟

如果您更喜欢可视化操作，可以直接启动全新开发的 **深色现代主题图形界面**：

```bash
# 安装完毕后，全局任意终端输入即可启动：
vd-gui
```
> **注意**：GUI 底层完全复用 CLI 的核心逻辑，支持播放列表控制、断点续传与画质选择，并集成了**实时进度条**和**终端日志动态输出**。
> *(Linux/WSL 下若想运行 GUI，请确保已安装 `python3-tk`)*

### 系统要求

| 依赖 | 用途 | 必需 |
|------|------|------|
| **Python** ≥ 3.10 | 运行环境 | ✅ |
| **ffmpeg** | 合并音视频轨（yt-dlp 需要） | ✅ |
| **Node.js** | Cookie 模式下解密 YouTube JS 签名 | 可选 |

---

## 🚀 使用示例

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
# 全自动下载 CS50 Python 全部章节
vd harvard --url "https://cs50.harvard.edu/python/"

# 指定画质
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

# KodeKloud
vd kodekloud --url "https://learn.kodekloud.com/user/courses/..." --cookies-file cookies.txt

# Skills Google
vd skillsgoogle --url "https://www.skills.google/paths/..." --cookies-file cookies.txt
```

---

## 🏗️ 项目结构

```
VideoDownloader/
├── pyproject.toml                # 包配置 & CLI 入口点定义
├── install.bat                   # Windows 一键安装脚本
├── requirements.txt              # 传统依赖清单
├── config.example.yaml           # 配置参考
├── main.py                       # 传统入口 (python main.py)
├── videodownloader/              # Python 包（pip install 后 vd 命令入口）
│   ├── __init__.py               # 版本号
│   ├── main.py                   # CLI 主程序
│   ├── core/
│   │   ├── cookies.py            # Cookie 管理（WSL/浏览器/文件）
│   │   ├── downloader.py         # 下载引擎（yt-dlp + requests + 断点续传）
│   │   └── utils.py              # 工具函数
│   └── plugins/
│       ├── base.py               # 插件抽象基类
│       ├── generic_ytdlp.py      # 通用 yt-dlp 插件（YouTube/Bilibili 等）
│       ├── harvard.py            # Harvard CS50 插件（MP4 直链优先）
│       ├── deeplearning_ai.py    # DeepLearning.AI 插件
│       ├── coursera.py           # Coursera 插件
│       ├── kodekloud.py          # KodeKloud 插件
│       └── skills_google.py      # Skills Google 插件
└── core/ & plugins/              # 传统路径 (向后兼容 python main.py)
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

> **WSL 用户**：安装 Chrome 扩展 [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)，访问目标网站后导出 `cookies.txt`。

> **提示**：下载公开视频（YouTube 免登录视频）时**无需** Cookie，省去 Cookie 参数反而更快。

---

## 📁 下载目录结构

```
downloads/
├── Norway 4K • Scenic Relaxation.mp4          # 通用单视频
├── Mix - Playlist Title/                      # YouTube 播放列表（自动创建子目录）
│   ├── 001 - Video Title 1.mp4
│   ├── 002 - Video Title 2.mp4
│   └── ...
├── CS50's Introduction to Programming/        # Harvard 课程（按周归档）
│   ├── 00 - Functions, Variables/
│   │   ├── 00 - Video_1.mp4
│   │   ├── Resource - lecture0.pdf
│   │   └── Resource - src0.zip
│   └── 01 - Conditionals/
│       └── ...
└── ai-for-everyone/                           # DeepLearning.AI 课程
    ├── Week_01/
    │   ├── 01_Introduction.mp4
    │   └── ...
    └── Week_02/
        └── ...
```

---

## 🔧 维护与升级

```bash
# YouTube 接口变化时，升级 yt-dlp 即可修复
pip install --upgrade yt-dlp

# 升级 VideoDownloader 本身（如果从 Git 拉取最新代码）
cd VideoDownloader && pip install -e .
```

---

## ✨ 特性一览

- 🎬 **多平台支持** — YouTube / Bilibili / Vimeo / Coursera / Harvard / DeepLearning.AI / KodeKloud / Skills Google + 任意 yt-dlp 支持的站点
- 📦 **播放列表批量下载** — 自动创建以列表名命名的子目录，支持 `--playlist-items` 切片
- 🎯 **画质选择** — 4K / 1080p Premium / 1080p / 720p / 480p / 纯音频
- 🔄 **断点续传** — 中断后重新运行自动从上次位置继续
- 🍪 **灵活鉴权** — 支持 cookies.txt 文件 / 浏览器直提 / 手动 Cookie 字符串
- 🛡️ **YouTube 反爬对抗** — 自动启用 Node.js + EJS solver 解密签名校验
- ⏭️ **容错跳过** — 播放列表中遇到不可用视频自动跳过，不中断整体下载
- 🖥️ **跨平台** — Linux / macOS / Windows (含 WSL)
- 🔌 **插件架构** — 实现 `BasePlugin` 接口即可扩展新平台

---

## 📖 技术文档 (Wiki)

查看深度技术文档以了解项目内部机制：
- [🏗️ 系统架构](docs/architecture.md) — 模块化设计与数据流。
- [🔌 插件开发](docs/plugins.md) — 如何支持一个新网站。
- [🌐 国际化流程](docs/i18n.md) — 了解 patch-based 翻译机制。
- [⚙️ 配置手册](docs/config.md) — `config.yaml` 高级参数说明。
- [🛠️ 开发与构建](docs/development.md) — 测试、编译与发布指南。

---

## ⚠️ 注意事项

- 本工具仅供**个人学习**使用，请遵守各平台服务条款
- 需要登录的内容必须提供有效 Cookie
- 并发数建议不超过 3，过高可能被平台限速
- 日志保存在 `download.log`

## 📄 License

MIT
