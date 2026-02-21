# VideoDownloader — 通用视频下载器
> 支持 YouTube、Bilibili、Vimeo、DeepLearning.AI、Coursera、KodeKloud 等任意 yt-dlp 支持的网站。

## 📦 安装依赖

```bash
pip install -r requirements.txt

# WSL 环境下若需自动解密 Chrome Cookie：
pip install pycryptodomex
```

## 🏗️ 项目结构

```
VideoDownloader/
├── main.py                  # CLI 入口
├── requirements.txt
├── config.example.yaml      # 配置参考
├── core/
│   ├── cookies.py           # Cookie 管理（WSL/浏览器/文件）
│   ├── downloader.py        # 下载引擎（yt-dlp + requests）
│   └── utils.py             # 工具函数
└── plugins/
    ├── base.py              # 插件抽象基类
    ├── deeplearning_ai.py   # DeepLearning.AI 插件
    ├── generic_ytdlp.py     # 通用 yt-dlp 插件
    ├── coursera.py          # Coursera 插件
    └── kodekloud.py         # KodeKloud 插件
```

## 🚀 快速开始

### 通用下载（YouTube/Bilibili/Vimeo 等）

```bash
# 下载公开视频（无需 Cookie）
python main.py download "https://www.youtube.com/watch?v=xxx"

# 指定画质
python main.py download "https://www.bilibili.com/video/BV1xx" -q 720p

# 下载字幕
python main.py download "https://www.youtube.com/watch?v=xxx" --subtitle

# 自定义输出目录 + 2 并发
python main.py download "https://..." -o ./my_videos -c 2
```

### DeepLearning.AI 课程

```bash
# 查看内置支持的课程
python main.py list-courses

# 下载全部课程（需 Cookie）
python main.py deeplearning --course ai-for-everyone --cookies-file cookies.txt

# 仅下载 Week 1 和 Week 2
python main.py deeplearning --course ai-for-everyone --weeks 1 2 --cookies-file cookies.txt
```

### Coursera 课程

```bash
python main.py coursera --url "https://www.coursera.org/learn/..." --cookies-file cookies.txt
```

### KodeKloud 课程

```bash
python main.py kodekloud --url "https://learn.kodekloud.com/user/courses/..." --cookies-file cookies.txt
```

## 🔑 Cookie 获取方法

| 方法 | 适用场景 |
|------|----------|
| `--cookies-file cookies.txt` | **WSL 推荐**，通过「Get cookies.txt LOCALLY」扩展导出 |
| `--browser chrome/brave/...` | 非 WSL 本机环境，自动从浏览器提取 |
| `--cookie "key=val; ..."` | 手动粘贴（DevTools → Application → Cookies） |

> **WSL 用户**：安装 Brave/Chrome 扩展 [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)，访问目标网站后导出 `cookies.txt`。

## 📋 全部参数

### 子命令通用参数
| 参数 | 说明 | 默认 |
|------|------|------|
| `-o, --output-dir` | 输出目录 | ./downloads |
| `-c, --concurrent` | 并发数 | 1 |
| `--cookies-file` | Cookie 文件路径 | - |
| `--cookie` | Cookie 字符串 | - |
| `-b, --browser` | 浏览器名称 | chrome |
| `-v, --verbose` | 调试日志 | 否 |

### `download` 特定参数
| 参数 | 说明 | 默认 |
|------|------|------|
| `-q, --quality` | 画质 (best/1080p/720p/480p/audio) | best |
| `--subtitle` | 下载字幕 | 否 |

### `kodekloud` 特定参数
| 参数 | 说明 | 默认 |
|------|------|------|
| `-q, --quality` | 画质 (1080p/720p/480p/360p) | 720p |

## 📁 下载目录结构

```
downloads/
├── ai-for-everyone/           # DeepLearning.AI 课程
│   ├── Week_01/
│   │   ├── 01_Introduction.mp4
│   │   └── ...
│   └── Week_02/
│       └── ...
├── Rick Astley - Never...mp4  # 通用下载
└── coursera_video.mp4
```

## ⚠️ 注意事项

- 本工具仅供**个人学习**使用，请遵守各平台服务条款
- 需要登录的内容必须提供有效 Cookie
- 并发数建议不超过 3，过高可能被平台限速
- 下载中断后重新运行会自动**断点续传**
- 日志保存在 `download.log`

## 🔧 扩展新平台

实现 `plugins/base.py` 中的 `BasePlugin` 接口即可。
