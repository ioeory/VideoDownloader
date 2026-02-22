#!/usr/bin/env python3
"""
DeepLearning.AI 课程视频下载插件
支持 learn.deeplearning.ai 上的所有课程。
提供内置课程结构 + 动态 API 获取两种模式。
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

import requests

from videodownloader.core.downloader import DownloadTask, build_session
from videodownloader.plugins.base import BasePlugin

log = logging.getLogger("videodownloader")

BASE_URL = "https://learn.deeplearning.ai"
API_BASE = f"{BASE_URL}/api"

# ─────────────────────────────────────────────
# 内置课程结构（免 API 模式）
# 格式: { course_slug: { "sections": [ { "name": str, "num": int, "lessons": [(slug, name)] } ] } }
# ─────────────────────────────────────────────

BUILTIN_COURSES: dict = {
    "ai-for-everyone": {
        "title": "AI for Everyone",
        "sections": [
            {
                "name": "Week 1 - Introduction",
                "num": 1,
                "lessons": [
                    ("week-1-introduction",        "01_Introduction"),
                    ("week-1-what-is-ai",          "02_What_is_AI"),
                    ("week-1-more-ai-terminology", "03_More_AI_Terminology"),
                    ("week-1-what-makes-ai-work",  "04_What_Makes_AI_Work"),
                    ("week-1-what-ai-can-cant-do", "05_What_AI_Can_and_Cant_Do"),
                    ("week-1-more-examples",       "06_More_Examples"),
                ],
            },
            {
                "name": "Week 2 - Building AI Projects",
                "num": 2,
                "lessons": [
                    ("week-2-workflow-of-a-ml-project",    "01_Workflow_of_ML_Project"),
                    ("week-2-workflow-of-a-ds-project",    "02_Workflow_of_DS_Project"),
                    ("week-2-every-job-function-needs-ai", "03_Every_Job_Function"),
                    ("week-2-case-study-smart-speaker",    "04_Case_Study_Smart_Speaker"),
                    ("week-2-case-study-self-driving-car", "05_Case_Study_Self_Driving_Car"),
                    ("week-2-example-roles-ai-team",       "06_Example_Roles_AI_Team"),
                    ("week-2-ai-transformation-playbook",  "07_AI_Transformation_Playbook"),
                    ("week-2-request-for-proposal",        "08_Request_for_Proposal"),
                ],
            },
            {
                "name": "Week 3 - Building AI in Your Company",
                "num": 3,
                "lessons": [
                    ("week-3-case-study-smart-speaker",    "01_Case_Study_Smart_Speaker"),
                    ("week-3-case-study-self-driving-car", "02_Case_Study_Self_Driving_Car"),
                    ("week-3-example-roles-ai-team",       "03_Example_Roles_AI_Team"),
                    ("week-3-ai-transformation-playbook",  "04_AI_Transformation_Playbook"),
                    ("week-3-pitfalls-to-avoid",           "05_Pitfalls_to_Avoid"),
                    ("week-3-taking-your-first-step",      "06_Taking_Your_First_Step"),
                ],
            },
            {
                "name": "Week 4 - AI and Society",
                "num": 4,
                "lessons": [
                    ("week-4-concerns-technology",   "01_Concerns_About_Technology"),
                    ("week-4-discrimination-bias",   "02_Discrimination_and_Bias"),
                    ("week-4-ai-developing-economies","03_AI_and_Developing_Economies"),
                    ("week-4-ai-jobs",               "04_AI_and_Jobs"),
                    ("week-4-conclusion",            "05_Conclusion"),
                ],
            },
        ],
    },
}


# ─────────────────────────────────────────────
# 工具函数：从页面/API 提取视频 URL
# ─────────────────────────────────────────────

def _deep_search(obj, keys: list) -> Optional[str]:
    """递归在嵌套 dict/list 中查找指定 key 的值"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and isinstance(v, str) and len(v) > 10:
                return v
            result = _deep_search(v, keys)
            if result:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = _deep_search(item, keys)
            if result:
                return result
    return None


def _extract_video_url_from_html(html: str) -> Optional[str]:
    """从页面 HTML 中提取视频 URL（m3u8/mp4）"""
    patterns = [
        r'"videoUrl"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'"videoUrl"\s*:\s*"([^"]+\.mp4[^"]*)"',
        r'"src"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'src:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'"video_url"\s*:\s*"([^"]+)"',
        r'https://[^"\']+vimeo[^"\']+",',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)

    # 查找内嵌 Next.js __NEXT_DATA__
    next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if next_data:
        try:
            data = json.loads(next_data.group(1))
            url = _deep_search(data, ["videoUrl", "video_url", "videoSrc", "src"])
            if url and any(ext in url for ext in ["mp4", "m3u8", "vimeo"]):
                return url
        except json.JSONDecodeError:
            pass
    return None


def _fetch_lesson_video_url(
    session: requests.Session, course_slug: str, lesson_slug: str
) -> Optional[str]:
    """通过 API 或 HTML 获取 lesson 视频 URL"""
    # 1. 尝试 API
    api_endpoints = [
        f"{API_BASE}/courses/{course_slug}/lessons/{lesson_slug}",
        f"{API_BASE}/lesson/{lesson_slug}",
        f"{BASE_URL}/api/v1/courses/{course_slug}/lessons/{lesson_slug}",
    ]
    for endpoint in api_endpoints:
        try:
            resp = session.get(endpoint, timeout=20)
            if resp.status_code == 200:
                url = _deep_search(
                    resp.json(),
                    ["videoUrl", "video_url", "url", "src", "streamUrl"],
                )
                if url:
                    log.info(f"API 获取视频 URL: {url[:60]}...")
                    return url
        except Exception:
            pass

    # 2. 解析 HTML 页面
    lesson_url = f"{BASE_URL}/courses/{course_slug}/lesson/quis4/{lesson_slug}"
    try:
        resp = session.get(lesson_url, timeout=30)
        resp.raise_for_status()
        url = _extract_video_url_from_html(resp.text)
        if url:
            return url
    except Exception as e:
        log.warning(f"HTML 页面解析失败 ({lesson_slug}): {e}")

    # 3. 兜底：把课程页面 URL 直接交给 yt-dlp
    return lesson_url


# ─────────────────────────────────────────────
# DeepLearning.AI 插件
# ─────────────────────────────────────────────

class DeepLearningPlugin(BasePlugin):
    """DeepLearning.AI 课程视频下载插件"""

    name = "deeplearning"
    description = "DeepLearning.AI 课程下载（learn.deeplearning.ai）"
    domains = ["learn.deeplearning.ai", "deeplearning.ai"]

    def get_cookies_domain(self) -> str:
        return ".deeplearning.ai"

    def get_download_tasks(
        self,
        url_or_id: str,
        output_dir: Path,
        cookies: Optional[dict] = None,
        course_slug: Optional[str] = None,
        weeks: Optional[list[int]] = None,
        **kwargs,
    ) -> list[DownloadTask]:
        """
        生成 DeepLearning.AI 课程下载任务列表。

        Args:
            url_or_id:   课程 URL 或课程 slug（如 'ai-for-everyone'）
            output_dir:  输出根目录
            cookies:     认证 Cookie
            course_slug: 课程 slug（若已知，优先使用）
            weeks:       指定 Week 列表，None 表示全部
        """
        # 解析课程 slug
        slug = course_slug or self._extract_slug(url_or_id)
        if not slug:
            raise ValueError(f"无法从输入解析课程 slug: {url_or_id}")

        log.info(f"准备下载课程: {slug}")

        # 获取课程结构
        course = BUILTIN_COURSES.get(slug)
        if not course:
            log.warning(
                f"课程 '{slug}' 无内置结构，将尝试直接下载主页面（功能受限）。\n"
                f"如需完整支持，请向 VideoDownloader 提交课程结构 PR。"
            )
            return [DownloadTask(
                url=f"{BASE_URL}/courses/{slug}",
                output_dir=output_dir / slug,
                filename=slug,
                cookies=cookies,
                cookie_domain=self.get_cookies_domain(),
                referer=BASE_URL,
            )]

        course_dir = output_dir / slug
        session = build_session(cookies or {}, referer=BASE_URL)
        tasks: list[DownloadTask] = []

        for section in course["sections"]:
            if kwargs.get("stop_check") and kwargs["stop_check"]():
                log.warning("🚫 任务解析已中止")
                break
                
            week_num = section["num"]
            if weeks and week_num not in weeks:
                continue

            week_dir = course_dir / f"Week_{week_num:02d}"
            for lesson_slug, lesson_name in section["lessons"]:
                if kwargs.get("stop_check") and kwargs["stop_check"]():
                    log.warning("🚫 任务解析已中止")
                    return tasks
                    
                video_url = _fetch_lesson_video_url(session, slug, lesson_slug)
                tasks.append(DownloadTask(
                    url=video_url or f"{BASE_URL}/courses/{slug}/lesson/quis4/{lesson_slug}",
                    output_dir=week_dir,
                    filename=lesson_name,
                    cookies=cookies,
                    cookie_domain=self.get_cookies_domain(),
                    referer=BASE_URL,
                    metadata={"course": slug, "week": week_num, "lesson": lesson_slug},
                ))

        log.info(f"共生成 {len(tasks)} 个下载任务")
        return tasks

    @staticmethod
    def _extract_slug(url_or_id: str) -> Optional[str]:
        """从 URL 或原始 slug 字符串中解析课程 slug"""
        # 直接是 slug
        if not url_or_id.startswith("http"):
            return url_or_id.strip("/")
        # 从 URL 中提取: /courses/{slug}/...
        match = re.search(r"/courses/([^/?#]+)", url_or_id)
        return match.group(1) if match else None

    def list_builtin_courses(self) -> list[str]:
        """列出所有内置课程 slug"""
        return list(BUILTIN_COURSES.keys())
