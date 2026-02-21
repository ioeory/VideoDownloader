#!/usr/bin/env python3
"""
通用下载引擎
- 主引擎：yt-dlp（支持 m3u8/mp4/直链/Vimeo/YouTube 等）
- 备用：requests 直接下载（纯 MP4 URL）
- 支持：断点续传、并发、进度条
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional

import requests
import yt_dlp
from tqdm import tqdm

from core.utils import HAS_FFMPEG, file_is_complete

log = logging.getLogger("videodownloader")


# ─────────────────────────────────────────────
# requests Session 构建
# ─────────────────────────────────────────────

DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def build_session(cookies: dict, referer: str = "") -> requests.Session:
    """构建带 Cookie 和浏览器 UA 的 requests Session"""
    session = requests.Session()
    session.cookies.update(cookies)
    session.headers.update({
        "User-Agent": DEFAULT_UA,
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    if referer:
        session.headers["Referer"] = referer
    return session


# ─────────────────────────────────────────────
# yt-dlp 下载
# ─────────────────────────────────────────────

def _write_netscape_cookies(cookies: dict, filepath: Path, domain: str) -> None:
    """将 Cookie dict 写入 Netscape 格式临时文件（供 yt-dlp 使用）"""
    lines = ["# Netscape HTTP Cookie File\n"]
    for name, value in cookies.items():
        lines.append(f"{domain}\tTRUE\t/\tFALSE\t2147483647\t{name}\t{value}\n")
    filepath.write_text("".join(lines))


def download_with_ytdlp(
    url: str,
    output_dir: Path,
    filename: str,
    cookies: Optional[dict] = None,
    cookie_domain: str = ".example.com",
    referer: str = "",
    extra_opts: Optional[dict] = None,
) -> bool:
    """
    使用 yt-dlp 下载视频（支持 m3u8/mp4/YouTube/Bilibili/Vimeo 等）

    Args:
        url:           视频 URL 或页面 URL（yt-dlp 自动提取）
        output_dir:    输出目录
        filename:      文件名（不含扩展名）
        cookies:       Cookie 字典（可选）
        cookie_domain: Cookie 所属域名（用于写 Netscape 文件）
        referer:       Referer 请求头
        extra_opts:    额外 yt-dlp 选项（会 merge 到默认配置）
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{filename}.mp4"

    if file_is_complete(output_file):
        log.info(f"⏭ 已存在，跳过: {output_file.name}")
        return True

    # 写临时 Cookie 文件
    cookie_file: Optional[Path] = None
    if cookies:
        with tempfile.NamedTemporaryFile(
            suffix=".txt", delete=False, mode="w", encoding="utf-8"
        ) as f:
            cookie_file = Path(f.name)
        _write_netscape_cookies(cookies, cookie_file, cookie_domain)

    ydl_opts: dict = {
        "outtmpl": str(output_dir / f"{filename}.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "retries": 5,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
        "noprogress": False,
        "overwrites": False,
        "http_headers": {
            "User-Agent": DEFAULT_UA,
        },
    }

    # 根据环境变量或检测结果决定格式（无 ffmpeg 则禁用合并）
    if HAS_FFMPEG:
        ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best"
    else:
        ydl_opts["format"] = "best[ext=mp4]/best"
        log.warning("未检测到 ffmpeg，将优先下载包含音轨的单文件（可能画质受限）")
    if cookie_file:
        ydl_opts["cookiefile"] = str(cookie_file)
    if referer:
        ydl_opts["http_headers"]["Referer"] = referer
    if extra_opts:
        ydl_opts.update(extra_opts)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        log.info(f"✅ 下载完成: {output_file.name}")
        return True
    except yt_dlp.utils.DownloadError as e:
        log.error(f"❌ yt-dlp 下载失败 ({filename}): {e}")
        return False
    finally:
        if cookie_file and cookie_file.exists():
            cookie_file.unlink(missing_ok=True)


# ─────────────────────────────────────────────
# requests 直接下载（备用，纯 MP4 直链）
# ─────────────────────────────────────────────

def download_with_requests(
    url: str,
    output_dir: Path,
    filename: str,
    session: Optional[requests.Session] = None,
) -> bool:
    """
    使用 requests 直接下载 MP4（备用方案）
    支持断点续传（Range 请求）
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{filename}.mp4"
    resume_pos = output_file.stat().st_size if output_file.exists() else 0

    sess = session or requests.Session()
    headers: dict = {}
    if resume_pos > 0:
        headers["Range"] = f"bytes={resume_pos}-"
        log.info(f"断点续传，从 {resume_pos} 字节继续: {filename}")

    try:
        with sess.get(url, headers=headers, stream=True, timeout=60) as resp:
            if resp.status_code == 416:
                log.info(f"⏭ 已完整下载，跳过: {filename}")
                return True
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0)) + resume_pos
            mode = "ab" if resume_pos > 0 else "wb"
            with open(output_file, mode) as f, tqdm(
                total=total,
                initial=resume_pos,
                unit="B",
                unit_scale=True,
                desc=filename[:40],
                ncols=80,
            ) as pbar:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        log.info(f"✅ 下载完成: {output_file.name}")
        return True
    except requests.RequestException as e:
        log.error(f"❌ requests 下载失败 ({filename}): {e}")
        return False


# ─────────────────────────────────────────────
# 任务数据类
# ─────────────────────────────────────────────

class DownloadTask:
    """表示一个视频下载任务"""

    def __init__(
        self,
        url: str,
        output_dir: Path,
        filename: str,
        cookies: Optional[dict] = None,
        cookie_domain: str = ".example.com",
        referer: str = "",
        metadata: Optional[dict] = None,
        extra_opts: Optional[dict] = None,
    ):
        self.url = url
        self.output_dir = output_dir
        self.filename = filename
        self.cookies = cookies
        self.cookie_domain = cookie_domain
        self.referer = referer
        self.metadata = metadata or {}
        self.extra_opts = extra_opts

    def run(self) -> tuple[str, bool]:
        """执行下载，返回 (filename, success)"""
        success = download_with_ytdlp(
            url=self.url,
            output_dir=self.output_dir,
            filename=self.filename,
            cookies=self.cookies,
            cookie_domain=self.cookie_domain,
            referer=self.referer,
            extra_opts=self.extra_opts,
        )
        return self.filename, success

    def __repr__(self) -> str:
        return f"DownloadTask({self.filename!r}, url={self.url!r})"
