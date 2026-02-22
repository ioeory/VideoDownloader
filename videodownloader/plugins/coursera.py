#!/usr/bin/env python3
"""
Coursera 课程视频下载插件（框架）

注意：Coursera 使用严格的 DRM 和动态视频 URL，直接下载受限。
本插件提供框架，依赖 yt-dlp 的 Coursera extractor 和有效的登录 Cookie。

使用前提：
  1. 在浏览器中登录 Coursera
  2. 导出 cookies.txt（推荐「Get cookies.txt LOCALLY」扩展）
  3. 运行: python main.py coursera --url "..." --cookies-file cookies.txt
"""

import logging
import re
from pathlib import Path
from typing import Optional

from videodownloader.core.downloader import DownloadTask
from videodownloader.plugins.base import BasePlugin

log = logging.getLogger("videodownloader")


class CourseraPlugin(BasePlugin):
    """Coursera 课程视频下载插件"""

    name = "coursera"
    description = "Coursera 课程下载（依赖 yt-dlp Coursera extractor + Cookie）"
    domains = ["coursera.org", "www.coursera.org"]

    def get_cookies_domain(self) -> str:
        return ".coursera.org"

    def get_download_tasks(
        self,
        url_or_id: str,
        output_dir: Path,
        cookies: Optional[dict] = None,
        quality: str = "best",
        subtitle: bool = True,
        **kwargs,
    ) -> list[DownloadTask]:
        """
        生成 Coursera 课程下载任务。

        Coursera 视频通过 yt-dlp 的内置 extractor 处理，
        支持单视频和整个课程的批量下载。

        Args:
            url_or_id: Coursera 视频/课程 URL
            output_dir: 输出目录
            cookies:   登录 Cookie（必须）
            quality:   画质（'best'/'720p'/'360p'）
            subtitle:  是否下载字幕
        """
        if not cookies:
            log.warning(
                "⚠️  Coursera 下载需要登录 Cookie！\n"
                "  请使用 --cookies-file 参数提供 cookies.txt 文件。"
            )

        url = url_or_id
        if not url.startswith("http"):
            url = f"https://www.coursera.org/learn/{url_or_id}"

        format_map = {
            "best":  "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "720p":  "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",
            "360p":  "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]",
        }

        extra_opts: dict = {
            "format": format_map.get(quality, format_map["best"]),
            # Coursera 播放列表支持
            "outtmpl": str(output_dir / "%(playlist_index)s_%(title)s.%(ext)s"),
        }
        if subtitle:
            extra_opts.update({
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["zh-Hans", "en"],
            })

        log.info(f"Coursera 任务: {url}")
        return [DownloadTask(
            url=url,
            output_dir=output_dir,
            filename="coursera_video",
            cookies=cookies,
            cookie_domain=self.get_cookies_domain(),
            referer="https://www.coursera.org/",
            extra_opts=extra_opts,
        )]
