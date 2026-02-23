import logging
import re
from pathlib import Path
from typing import List, Optional

import requests

from videodownloader.core.downloader import DownloadTask
from videodownloader.core.utils import HAS_FFMPEG, sanitize_filename
from videodownloader.plugins.base import BasePlugin

log = logging.getLogger("videodownloader")

class KodeKloudPlugin(BasePlugin):
    name = "kodekloud"
    description = "KodeKloud 课程下载 (learn.kodekloud.com)"
    domains = ["learn.kodekloud.com", "kodekloud.com"]

    def can_handle(self, url: str) -> bool:
        return any(domain in url for domain in self.domains)

    def get_cookies_domain(self) -> str:
        return "learn.kodekloud.com"

    def _get_token(self, cookies: dict) -> str:
        """从 cookies 中获取 session-cookie (JWT)"""
        # 如果用户直接拷贝了一串长 token，且被正确提取为 __raw_token__
        if "__raw_token__" in cookies:
            return cookies["__raw_token__"]
            
        token = cookies.get("session-cookie")
        if not token:
            # 尝试从原始 cookie 字典中查找
            for key, val in cookies.items():
                if key.lower() == "session-cookie":
                    return val
        return token

    def get_download_tasks(
        self,
        url_or_id: str,
        output_dir: Path,
        cookies: Optional[dict] = None,
        quality: str = "720p",
        **kwargs
    ) -> List[DownloadTask]:
        if not cookies:
            log.error(self._t("log_cookie_required", "🚫 Cookie required for this platform.", **kwargs))
            return []

        token = self._get_token(cookies)
        if not token:
            log.error(self._t("log_session_cookie_missing", "🚫 Missing 'session-cookie' in your cookies. Make sure you are logged in.", **kwargs))
            return []

        # 提取 course slug
        # 支持: https://learn.kodekloud.com/user/courses/ai-assisted-ansible
        course_slug = url_or_id.strip("/").split("/")[-1]
        log.info(self._t("log_fetching_course_info", "⏳ Fetching course info: {}", course_slug, **kwargs))

        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://learn.kodekloud.com/",
        }

        # 1. 获取课程结构
        course_api = f"https://learn-api.kodekloud.com/api/courses/{course_slug}"
        try:
            r = requests.get(course_api, headers=headers, timeout=15)
            r.raise_for_status()
            course_data = r.json()
        except Exception as e:
            log.error(self._t("log_course_structure_error", "❌ Failed to fetch course structure: {}", e, **kwargs))
            return []

        course_title = course_data.get("title", course_slug)
        modules = course_data.get("modules", [])
        log.info(self._t("log_modules_found", "Found {} modules", len(modules), **kwargs))

        tasks = []
        course_path = output_dir / sanitize_filename(course_title)

        for m_idx, module in enumerate(modules, 1):
            if kwargs.get("stop_check") and kwargs["stop_check"]():
                log.warning(self._t("log_parsing_aborted", "🚫 Task parsing aborted", **kwargs))
                break
                
            module_title = module.get("title", f"Module {m_idx}")
            module_path = course_path / f"{m_idx:02d} - {sanitize_filename(module_title)}"
            
            lessons = module.get("lessons", [])
            for l_idx, lesson in enumerate(lessons, 1):
                if kwargs.get("stop_check") and kwargs["stop_check"]():
                    log.warning(self._t("log_parsing_aborted", "🚫 Task parsing aborted", **kwargs))
                    return tasks
                    
                lesson_title = lesson.get("title", f"Lesson {l_idx}")
                lesson_id = lesson.get("id")
                lesson_type = lesson.get("type", "video")

                if lesson_type != "video":
                    log.debug(self._t("log_skipping_non_video", "⏭ Skipping non-video content: {}", lesson_title, **kwargs))
                    continue

                log.info(self._t("log_getting_lesson_video", "⏳ Getting video ID for lesson: {}", lesson_title, **kwargs))
                lesson_api = f"https://learn-api.kodekloud.com/api/lessons/{lesson_id}"
                try:
                    # 使用与获取课程相同的 headers (含 JWT)
                    lr = requests.get(lesson_api, headers=headers, params={"course_id": course_data.get("id")}, timeout=10)
                    lr.raise_for_status()
                    lesson_data = lr.json()
                    
                    # 获取 video_url，通常类似 "https://vimeo.com/123456789"
                    video_url_raw = lesson_data.get("video_url")
                    if not video_url_raw:
                        log.warning(self._t("log_video_url_not_found", "⚠️ No video URL found for lesson: {}", lesson_title, **kwargs))
                        continue

                    # 转换为 Vimeo 播放器地址或保持原样
                    # KodeKloud 的 video_url 可能是 vimeo ID 或完整 vimeo link
                    if "vimeo.com" in video_url_raw:
                        vimeo_id = video_url_raw.split("/")[-1]
                        vimeo_url = f"https://player.vimeo.com/video/{vimeo_id}"
                    else:
                        vimeo_url = f"https://player.vimeo.com/video/{video_url_raw}"

                    filename = f"{l_idx:02d} - {sanitize_filename(lesson_title)}"
                    
                    h = int(quality[:-1]) if quality.endswith("p") else 720
                    if HAS_FFMPEG:
                        # 兼容 vimeo HLS：音频可能被标识为 mp4 而非 m4a
                        fmt = f"bestvideo[height<={h}][ext=mp4]+bestaudio/best[height<={h}][ext=mp4]/best[height<={h}]/best"
                    else:
                        fmt = f"best[height<={h}][ext=mp4]/best[height<={h}]/best"

                    tasks.append(DownloadTask(
                        url=vimeo_url,
                        output_dir=module_path,
                        filename=filename,
                        cookies=cookies,
                        cookie_domain=".vimeo.com",
                        referer="https://learn.kodekloud.com/",
                        extra_opts={
                            "format": fmt
                        }
                    ))
                except Exception as e:
                    log.error(self._t("log_lesson_failed", "❌ Failed for lesson {}: {}", lesson_title, e, **kwargs))

        return tasks
