#!/usr/bin/env python3
"""
通用 yt-dlp 插件
支持 YouTube、Bilibili、Vimeo、Twitter/X、TikTok 等任意 yt-dlp 支持的网站。
对于无需特殊认证的公开视频，无需提供 Cookie。
"""

import logging
import re
from pathlib import Path
from typing import Optional

from videodownloader.core.downloader import DownloadTask
from videodownloader.core.utils import sanitize_filename
from videodownloader.plugins.base import BasePlugin

log = logging.getLogger("videodownloader")


class GenericYtdlpPlugin(BasePlugin):
    """
    通用 yt-dlp 插件
    可直接传入任意 URL，由 yt-dlp 自动识别并下载。
    """

    name = "generic"
    description = "通用 yt-dlp 插件（YouTube / Bilibili / Vimeo / 任意支持网站）"
    domains = []  # 空表示匹配所有 URL（兜底插件）

    def can_handle(self, url: str) -> bool:
        """通用插件作为兜底，始终返回 True"""
        return True

    def get_download_tasks(
        self,
        url_or_id: str,
        output_dir: Path,
        cookies: Optional[dict] = None,
        quality: str = "best",
        subtitle: bool = False,
        filename: str = "",
        playlist_items: Optional[str] = None,
    ) -> list[DownloadTask]:
        """
        生成通用下载任务。

        Args:
            url_or_id: 视频 URL
            output_dir: 输出目录
            cookies:   Cookie（可选，用于需要登录的网站）
            filename:  自定义文件名（不含扩展名），默认用视频标题
            quality:   画质选项（'best'/'1080p'/'720p' 等）
            subtitle:  是否下载字幕
            playlist_items: 播放列表项目范围（例如 "1-5", "1,3,5", "all"）
        """
        url = url_or_id

        # 自动生成文件名（从 URL 提取或用 yt-dlp 模板）
        if not filename:
            filename = "%(title)s"

        # 根据画质设置 yt-dlp format
        format_map = {
            "best":  "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
            "4k":    "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best[height<=2160]/best",
            "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "720p":  "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "480p":  "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]/best",
            "audio": "bestaudio[ext=m4a]/bestaudio/best",
        }
        fmt = format_map.get(quality, format_map["best"])

        extra_opts: dict = {"format": fmt}
        if subtitle:
            extra_opts.update({
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["zh-Hans", "zh-Hant", "en"],
            })

        # 检测是否是播放列表
        is_playlist = any(kw in url for kw in ["list=", "playlist", "/playlist/"])
        if is_playlist:
            log.info(f"检测到播放列表，将批量下载: {url}")
            # 存放在以播放列表名称为名字的独立文件夹中
            extra_opts["outtmpl"] = str(output_dir / "%(playlist_title)s" / "%(playlist_index)03d - %(title)s.%(ext)s")
            extra_opts["noplaylist"] = False
            if playlist_items:
                extra_opts["playlist_items"] = playlist_items
            # 播放列表：单任务（yt-dlp 内部处理多个视频）
            return [DownloadTask(
                url=url,
                output_dir=output_dir,
                filename="playlist",
                cookies=cookies,
                extra_opts=extra_opts,
            )]

        return [DownloadTask(
            url=url,
            output_dir=output_dir,
            filename=filename,
            cookies=cookies,
            extra_opts=extra_opts,
        )]

    def get_cookies_domain(self) -> str:
        return ".example.com"
