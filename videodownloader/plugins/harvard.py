import logging
import re
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin, unquote

import requests
from bs4 import BeautifulSoup

from videodownloader.core.downloader import DownloadTask
from videodownloader.core.utils import sanitize_filename
from videodownloader.plugins.base import BasePlugin

log = logging.getLogger("videodownloader")

class HarvardPlugin(BasePlugin):
    name = "harvard"
    description = "Harvard.edu 课程视频及资料下载 (如 cs50.harvard.edu)"
    domains = ["harvard.edu"]

    def can_handle(self, url: str) -> bool:
        return any(domain in url for domain in self.domains)

    def get_cookies_domain(self) -> str:
        return ".harvard.edu"

    def get_download_tasks(
        self,
        url_or_id: str,
        output_dir: Path,
        cookies: Optional[dict] = None,
        quality: str = "best",
        **kwargs
    ) -> List[DownloadTask]:

        url = url_or_id
        session = requests.Session()
        if cookies:
            for k, v in cookies.items():
                session.cookies.set(k, v)
        
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

        log.info(self._t("log_extracting_info", "⏳ Extracting video info: {}", url, **kwargs))
        try:
            r = session.get(url, timeout=15)
            r.raise_for_status()
            html = r.text
        except Exception as e:
            log.error(self._t("log_html_failed", "HTML parsing failed ({}): {}", url, e, **kwargs))
            return []

        soup = BeautifulSoup(html, "html.parser")
        course_title = sanitize_filename(soup.title.string.strip()) if soup.title else "Harvard_Course"
        course_dir = output_dir / course_title

        tasks = []
        
        # 探测是否是索引页（包含多个 weeks/ 链接）
        week_links = []
        for a in soup.find_all("a", href=True):
            href = a['href']
            if re.search(r'weeks/\d+/?$', href.split('#')[0]):
                full_url = urljoin(url, href)
                if full_url not in [w[0] for w in week_links]:
                    week_links.append((full_url, a.text.strip()))
        
        is_week_page = bool(re.search(r'weeks/\d+/?$', url.split('#')[0]))
        
        if not is_week_page and week_links:
            log.info(self._t("log_playlist_detected", "📚 Playlist detected, starting batch extraction...", **kwargs))
            for idx, (w_url, w_text) in enumerate(week_links, start=0):
                # 自动为每一个子章节补充数字序号前缀，确保可以稳固按序排序，避免同名或缺失 Week 标识
                safe_text = sanitize_filename(w_text) if w_text else "Chapter"
                prefix = f"{idx:02d} - {safe_text}"
                
                log.info(self._t("log_starting_task", "Starting task [{}/{}]: {}", idx+1, len(week_links), prefix, **kwargs))
                try:
                    wr = session.get(w_url, timeout=15)
                    wr.raise_for_status()
                    week_dir = course_dir / prefix
                    sub_tasks = self._parse_page_content(wr.text, w_url, week_dir, cookies, quality, **kwargs)
                    tasks.extend(sub_tasks)
                except Exception as e:
                    log.error(self._t("log_html_failed", "HTML parsing failed ({}): {}", w_url, e, **kwargs))
            return tasks
        else:
            log.info(self._t("log_starting_ytdlp", "⏳ Starting yt-dlp queue for {}", course_title, **kwargs))
            return self._parse_page_content(html, url, course_dir, cookies, quality, **kwargs)

    def _parse_page_content(self, html: str, url: str, course_dir: Path, cookies: Optional[dict], quality: str) -> List[DownloadTask]:
        soup = BeautifulSoup(html, "html.parser")
        tasks = []
        seen_urls = set()

        # 1. 优先查找直接的 MP4 视频链接（避免 YouTube 反爬机制）
        # CS50 经常提供不同分辨率 (360p, 720p, 1080p, 4K) 的直接 mp4 文件链接，且分 SDR/HDR
        mp4_groups = {}
        for a in soup.find_all("a", href=True):
            href = a['href']
            if href.lower().split('?')[0].endswith('.mp4'):
                text = a.text.strip().lower()
                # 分组提取 base url，去除分辨率后缀，如 -1080p, -4k-hdr
                base = re.sub(r'-(4k|1080p|720p|360p|sdr|hdr).*$', '', href.split('?')[0])
                if base not in mp4_groups:
                    mp4_groups[base] = []
                mp4_groups[base].append((href, text))

        video_links = []
        if mp4_groups:
            log.info(self._t("log_api_url", "API got video URL: {}...", f"MP4 Batch ({len(mp4_groups)})", **kwargs))
            for base, links in mp4_groups.items():
                sdr_links = [link for link in links if "hdr" not in link[0].lower()]
                pool = sdr_links if sdr_links else links
                
                preferred_mp4 = None
                target_q = "1080p" if quality.lower() == "best" else quality.lower()
                
                # 精确匹配目标质量
                matched = [link for link in pool if target_q in link[1] or target_q in link[0].lower()]
                if matched:
                    preferred_mp4 = matched[0][0]
                else:
                    # 兜底匹配常见分辨率
                    for q in ["1080p", "720p", "4k", "360p"]:
                        matched = [link for link in pool if q in link[1] or q in link[0].lower()]
                        if matched:
                            preferred_mp4 = matched[0][0]
                            break
                    if not preferred_mp4:
                        preferred_mp4 = pool[0][0]
                
                video_links.append((preferred_mp4, "Video"))
        else:
            # 2. 如果没有 MP4 链接，回退到查找 YouTube / Vimeo 链接
            log.info(self._t("log_playlist_detected", "📚 Playlist detected, starting batch extraction...", **kwargs))
            for a in soup.find_all("a", href=True):
                href = a['href']
                if "youtube.com" in href or "youtu.be" in href or "vimeo.com" in href:
                    if "subscription_center" in href or "user=" in href or "@" in href:
                        continue
                    video_links.append((href, a.text.strip() or "video"))
            
            for iframe in soup.find_all("iframe", src=True):
                src = iframe['src']
                if "youtube.com" in src or "youtu.be" in src or "vimeo.com" in src:
                    src_unquoted = unquote(src)
                    if src_unquoted.startswith("//"):
                        src_unquoted = f"https:{src_unquoted}"
                    video_links.append((src_unquoted, "video"))

        for idx, (v_url, v_text) in enumerate(video_links, 1):
            if v_url not in seen_urls:
                seen_urls.add(v_url)
                name_part = sanitize_filename(v_text) if v_text.lower() not in ('video', 'youtube') else f'Video_{idx}'
                filename = f"{idx:02d} - {name_part}"
                # 如果是 YouTube 的公开视频，避免防反爬
                is_yt = ('youtube.com' in v_url or 'youtu.be' in v_url)
                task_cookies = None if is_yt else cookies
                tasks.append(self._create_task(v_url, course_dir, filename, task_cookies, quality, ignore_global_cookies=is_yt))

        # 3. 查找静态文件资料 (.pdf, .txt, .zip 等)
        for a in soup.find_all("a", href=True):
            href = a['href']
            full_url = urljoin(url, href)
            # 对于 mp4 文件在前面已经处理这里需要排除
            ext = full_url.split('?')[0].split('.')[-1].lower()
            if ext in ['pdf', 'txt', 'zip', 'csv']:
                if full_url not in seen_urls:
                    seen_urls.add(full_url)
                    raw_filename = full_url.split('?')[0].split('/')[-1]
                    base_filename = raw_filename.rsplit('.', 1)[0] if '.' in raw_filename else sanitize_filename(a.text.strip() or f"file_{len(seen_urls)}")
                    filename_with_prefix = f"Resource - {sanitize_filename(base_filename)}"
                    
                    log.info(self._t("log_start_requests", "⏳ Starting download: {}", full_url, **kwargs))
                    tasks.append(DownloadTask(
                        url=full_url,
                        output_dir=course_dir,
                        filename=filename_with_prefix,
                        cookies=cookies
                    ))

        return tasks

    def _create_task(self, url: str, course_dir: Path, filename: str, cookies: Optional[dict], quality: str, ignore_global_cookies: bool = False) -> DownloadTask:
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
            extra_opts=opts,
            ignore_global_cookies=ignore_global_cookies
        )
