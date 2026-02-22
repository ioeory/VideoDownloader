import logging
import re
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin, unquote

import requests

from core.downloader import DownloadTask
from core.utils import sanitize_filename
from plugins.base import BasePlugin

log = logging.getLogger("videodownloader")

class SkillsGooglePlugin(BasePlugin):
    name = "skills_google"
    description = "Skills Google 课程下载 (skills.google / cloudskillsboost.google)"
    domains = ["skills.google", "cloudskillsboost.google", "exceedlms.com"]

    def can_handle(self, url: str) -> bool:
        return any(domain in url for domain in self.domains)

    def get_cookies_domain(self) -> str:
        return ".skills.google"

    def get_download_tasks(
        self,
        url_or_id: str,
        output_dir: Path,
        cookies: Optional[dict] = None,
        quality: str = "best",
        **kwargs
    ) -> List[DownloadTask]:
        if not cookies:
            log.warning("未提供 Cookie，可能会重定向到登录页无法解析。")

        url = url_or_id
        session = requests.Session()
        if cookies:
            # Add cookies to session
            for k, v in cookies.items():
                session.cookies.set(k, v)
        
        # 为了应对反爬或简单的登录跳转
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })

        log.info(f"正在获取页面内容: {url}")
        try:
            r = session.get(url, timeout=15)
            r.raise_for_status()
            html = r.text
        except Exception as e:
            log.error(f"无法获取页面 {url}: {e}")
            return []

        # 尝试提取页面标题名作为课程名
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        course_title = sanitize_filename(title_match.group(1).split('|')[0].strip()) if title_match else "SkillsGoogle_Course"
        course_dir = output_dir / course_title

        tasks = []
        
        # 匹配 <ql-activity-card ... path='...' ... type='video'>
        # 形式可能是 path='/paths/1951/course_templates/1268/video/618296'
        cards = re.findall(r'<ql-activity-card[^>]*type=[\'"]video[\'"][^>]*>', html, re.IGNORECASE)
        
        if cards:
            log.info(f"检测到课程模板页，找到 {len(cards)} 个视频卡片")
            for idx, card in enumerate(cards, start=1):
                path_m = re.search(r'path=[\'"]([^\'"]+)[\'"]', card)
                name_m = re.search(r'name=[\'"]([^\'"]+)[\'"]', card)
                
                if path_m:
                    video_page_path = path_m.group(1)
                    video_page_url = urljoin(url, video_page_path)
                    video_name = name_m.group(1) if name_m else f"Video_{idx}"
                    
                    log.info(f"正在解析子视频页: {video_name} ({video_page_url})")
                    try:
                        vr = session.get(video_page_url, timeout=10)
                        vr.raise_for_status()
                        v_html = vr.text
                        
                        # 在子页面中找 iframe 的 youtube 或其他视频源
                        actual_video_url = self._extract_video_embed(v_html)
                        if actual_video_url:
                            filename = f"{idx:02d} - {sanitize_filename(video_name)}"
                            tasks.append(self._create_task(actual_video_url, course_dir, filename, cookies, quality))
                        else:
                            log.warning(f"在 {video_page_url} 未找到嵌入式视频 URL (iframe src 等)")
                    except Exception as e:
                        log.error(f"获取视频页面 {video_page_url} 失败: {e}")
        else:
            # 可能当前页面就是一个单一视频页
            log.info("未检测到多视频卡片，尝试作为单一视频页面解析")
            actual_video_url = self._extract_video_embed(html)
            if actual_video_url:
                tasks.append(self._create_task(actual_video_url, course_dir, course_title, cookies, quality))
            else:
                log.warning(f"页面 {url} 未找到支持下载的视频嵌入链接 (iframe src 等)")

        return tasks

    def _extract_video_embed(self, html: str) -> Optional[str]:
        # 寻找技能平台定制的 YouTube 组件: <ql-youtube-video videoId='XXXX'>
        ql_yt_match = re.search(r'<ql-youtube-video[^>]*videoId=[\'"]([a-zA-Z0-9_-]+)[\'"][^>]*>', html, re.IGNORECASE)
        if ql_yt_match:
            return f"https://www.youtube.com/watch?v={ql_yt_match.group(1)}"

        # 寻找技能平台定制的 Wistia 组件: <ql-wistia-video videoId='XXXX'>
        ql_wistia_match = re.search(r'<ql-wistia-video[^>]*videoId=[\'"]([a-zA-Z0-9_-]+)[\'"][^>]*>', html, re.IGNORECASE)
        if ql_wistia_match:
            # yt-dlp 兼容 wistia 链接
            return f"http://fast.wistia.net/embed/iframe/{ql_wistia_match.group(1)}"

        # 优先寻找 YouTube / Vimeo iframe
        iframe_srcs = re.findall(r'<iframe[^>]+src=[\'"]([^\'"]+)[\'"]', html, re.IGNORECASE)
        for src in iframe_srcs:
            src_unquoted = unquote(src)
            if "youtube.com/embed" in src_unquoted or "youtu.be" in src_unquoted or "vimeo.com" in src_unquoted:
                # 规范化 URL
                if src_unquoted.startswith("//"):
                    return f"https:{src_unquoted}"
                return src_unquoted
            
        # 寻找 HTML5 <video> 标签中的 src 或 source 标签
        video_srcs = re.findall(r'<video[^>]+src=[\'"]([^\'"]+)[\'"]|<source[^>]+src=[\'"]([^\'"]+)[\'"]', html, re.IGNORECASE)
        for v_src in video_srcs:
            v = v_src[0] or v_src[1]
            if v and v.endswith((".mp4", ".m3u8", ".webm")):
                return v

        # 暴力寻找 youtube 链接（即使不在 iframe 中）
        yt_match = re.search(r'(https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]+)', html)
        if yt_match:
            return yt_match.group(1)

        return None

    def _create_task(self, url: str, course_dir: Path, filename: str, cookies: Optional[dict], quality: str) -> DownloadTask:
        # 对 youtube/vimeo 等平台，其实不再需要 skills.google 的 cookie，但可以带上
        # 我们使用 yt-dlp 来提取
        h = int(quality[:-1]) if quality.endswith("p") else 1080
        fmt = f"bestvideo[height<={h}][ext=mp4]+bestaudio/best[height<={h}][ext=mp4]/best[height<={h}]/best" if quality != "best" else "best"
        
        opts = {
            "format": fmt
        }
        
        return DownloadTask(
            url=url,
            output_dir=course_dir,
            filename=filename,
            cookies=cookies,
            extra_opts=opts
        )
