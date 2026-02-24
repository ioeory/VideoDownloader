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

from videodownloader.core.utils import HAS_FFMPEG, FFMPEG_PATH, file_is_complete, UserStoppedException

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
    playlist_count_callback=None,
) -> str:
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

    # Note: 此时我们尚不知晓文件的最终具体大小，先检查基础存在性。
    # 稍后我们将通过 yt-dlp extract_info 获取预期大小进行严格校验。
    # 但如果为了防覆盖且不检查字节直接跳过，可能误判未完成的文件。
    # 因此我们会依赖 yt-dlp 自带的断点续传机制，这里不再简单判断 file_is_complete。

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
        "quiet": False,  # 允许输出进度条与提示
        "no_warnings": True,
        "retries": 5,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
        "noprogress": False,
        "overwrites": False,
        "noplaylist": True,  # 强制不下载播放列表，防止互相覆盖
        "ignoreerrors": True, # 遇到不可用视频时跳过，防止阻塞整个列表
        "http_headers": {
            "User-Agent": DEFAULT_UA,
        },
    }

    # 启用 Node.js 运行时 + EJS challenge solver（解决 Cookie 模式下 YouTube 签名校验问题）
    import shutil
    import sys
    import os
    
    # 兼容 PyInstaller 打包时解压 Node.js 的目录查找
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        meipass_node = Path(sys._MEIPASS) / ("node.exe" if os.name == 'nt' else "node")
        if meipass_node.exists():
            # 将 _MEIPASS 放到 PATH 最前面，确保 yt-dlp 能找到打包自带的 node
            os.environ["PATH"] = str(sys._MEIPASS) + os.pathsep + os.environ.get("PATH", "")

    if shutil.which("node"):
        ydl_opts["js_runtimes"] = {"node": {}}
        ydl_opts["remote_components"] = ["ejs:github"]

    # 获取翻译器（如果由 GUI 注入）
    t = extra_opts.get("translator") if extra_opts else None
    def _t(key, default, *args):
        if t: return t(key).format(*args)
        return default.format(*args)

    # 根据环境变量或检测结果决定格式（无 ffmpeg 则禁用合并）
    if HAS_FFMPEG:
        ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio/bestvideo+bestaudio/best"
        if FFMPEG_PATH:
            ydl_opts["ffmpeg_location"] = FFMPEG_PATH
    else:
        ydl_opts["format"] = "best[ext=mp4]/best"
        log.warning(_t("log_no_ffmpeg", "ffmpeg not found. Priority will be single file with audio (quality might be limited)."))
    if cookie_file:
        ydl_opts["cookiefile"] = str(cookie_file)
    if referer:
        ydl_opts["http_headers"]["Referer"] = referer
    if extra_opts:
        ydl_opts.update(extra_opts)

    # GUI 模式下大段的 JSON 配置会刷屏，由于已稳定运行，移除此条 Debug 日志让视觉更清晰
    
    try:
        log.info(_t("log_extracting_info", "⏳ Extracting video info: {}", url))
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if "noplaylist" not in ydl_opts or ydl_opts["noplaylist"]:
                # 只有单文件时提取信息以校验大小
                info_dict = ydl.extract_info(url, download=False)
                if not info_dict:
                    log.error(_t("log_extract_failed", "❌ Failed to extract info for {} (empty result)", filename))
                    return "error"

                entries = info_dict.get('entries')
                if entries:
                    video_info = entries[0]
                else:
                    video_info = info_dict

                # 尝试获取视频大小
                expected_size = video_info.get("filesize") or video_info.get("filesize_approx")
                
                if output_file.exists():
                    actual_size = output_file.stat().st_size
                    if expected_size and actual_size < expected_size * 0.90:
                        log.warning(_t("log_file_incomplete", "⚠️ File incomplete: Actual {} < Expected {} (90%). Resuming download for: {}", actual_size, expected_size, output_file.name))
                        part_file = output_file.with_suffix(output_file.suffix + ".part")
                        output_file.rename(part_file)
                    elif expected_size is None and actual_size <= 1024:
                        log.warning(_t("log_file_too_small", "⚠️ File too small (<1KB), deleting and redownloading: {}", output_file.name))
                        output_file.unlink()
                    else:
                        log.info(_t("log_skip_complete", "⏭ Skip already downloaded: {}", output_file.name))
                        return "success"
            else:
                expected_size = None # 忽略播放列表的预估大小
                # 快速预扫描播放列表获取项目总数，通知 GUI 旴新进度条
                try:
                    flat_info = ydl.extract_info(url, download=False, process=False)
                    entries = flat_info.get('entries') or []
                    n = len(list(entries)) if hasattr(entries, '__iter__') else flat_info.get('n_entries', 0)
                    if not n:
                        n = flat_info.get('n_entries') or flat_info.get('playlist_count') or 0
                    if n and n > 1 and playlist_count_callback:
                        playlist_count_callback(int(n))
                        log.info(_t("log_playlist_prescan", "📊 Playlist pre-scan complete, found {} entries", n))
                except Exception as pre_e:
                    log.debug(f"播放列表预扫描失败 (不影响下载): {pre_e}")
                log.info(_t("log_playlist_detected", "📚 Playlist detected, starting batch extraction..."))

            log.info(_t("log_starting_ytdlp", "⏳ Starting yt-dlp queue for {} (URL: {})", filename, url))
            # 现在正式执行下载
            retcode = ydl.download([url])

        # 下载后再次通过 filesize 校验本地文件是否符合预期，防止网络问题残缺
        if expected_size and output_file.exists():
             actual_size = output_file.stat().st_size
             if actual_size < expected_size * 0.90: # 简单容差
                 log.warning(_t("log_size_mismatch", "⚠️ Downloaded file ({} bytes) is much smaller than expected ({} bytes), please check {}", actual_size, expected_size, output_file.name))
        
        log.info(_t("log_download_complete", "✅ Download complete: {} (URL: {})", output_file.name, url))
        return "success"
    except UserStoppedException:
        log.info(_t("log_user_stopped_dl", "🚫 User stopped download: {}", filename))
        return "error"
    except yt_dlp.utils.DownloadError as e:
        log.error(_t("log_ytdlp_failed", "❌ yt-dlp download failed ({}): {}", filename, e))
        return "error"
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
    ext: str = "mp4",
    session: Optional[requests.Session] = None,
    progress_hooks: Optional[list] = None,
    extra_opts: Optional[dict] = None,
) -> str:
    """
    使用 requests 直接下载（备用方案）
    支持断点续传（Range 请求）及进度钩子（用于暂定/停止）
    """
    t = extra_opts.get("translator") if extra_opts else None
    def _t(key, default, *args):
        if t: return t(key).format(*args)
        return default.format(*args)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{filename}.{ext}"
    resume_pos = output_file.stat().st_size if output_file.exists() else 0

    sess = session or requests.Session()
    headers: dict = {}
    if resume_pos > 0:
        headers["Range"] = f"bytes={resume_pos}-"
        log.info(_t("log_resume_requests", "Resuming from {} bytes: {}", resume_pos, filename))

    try:
        with sess.get(url, headers=headers, stream=True, timeout=60) as resp:
            if resp.status_code == 416:
                log.info(_t("log_skip_complete", "⏭ Skip already downloaded: {}", filename))
                return "success"
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0)) + resume_pos
            mode = "ab" if resume_pos > 0 else "wb"
            log.info(_t("log_start_requests", "⏳ Starting download: {} (URL: {})", output_file.name, url))
            desc_name = (output_file.name[:25] + "..." + output_file.name[-10:]) if len(output_file.name) > 40 else output_file.name
            
            show_tqdm = True
            if extra_opts and extra_opts.get("noprogress"):
                show_tqdm = False

            with open(output_file, mode) as f, tqdm(
                total=total,
                initial=resume_pos,
                unit="B",
                unit_scale=True,
                desc=desc_name,
                ncols=100,
                disable=not show_tqdm,
            ) as pbar:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    # Check pause/abort via hooks
                    if progress_hooks:
                        mock_d = {
                            "status": "downloading",
                            "downloaded_bytes": pbar.n,
                            "total_bytes": total,
                            "filename": str(output_file),
                            "_speed_str": "N/A (requests)"
                        }
                        for hook in progress_hooks:
                            try:
                                hook(mock_d)
                            except BaseException as hook_err:
                                if "USER_STOPPED" in str(hook_err) or isinstance(hook_err, UserStoppedException):
                                    log.info(_t("log_user_stopped_dl", "🚫 User stopped download: {}", filename))
                                    return "error"
                                raise hook_err
                                
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
                        
        if progress_hooks:
            mock_d = {"status": "finished", "filename": str(output_file)}
            for hook in progress_hooks:
                try: hook(mock_d)
                except: pass
                
        log.info(_t("log_download_complete", "✅ Download complete: {} (URL: {})", output_file.name, url))
        return "success"
    except UserStoppedException:
        log.info(_t("log_user_stopped_dl", "🚫 User stopped download: {}", filename))
        return "error"
    except requests.RequestException as e:
        log.error(_t("log_requests_failed", "❌ requests download failed ({}): {}", filename, e))
        return "error"


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
        ignore_global_cookies: bool = False,
    ):
        self.url = url
        self.output_dir = output_dir
        self.filename = filename
        self.cookies = cookies
        self.cookie_domain = cookie_domain
        self.referer = referer
        self.metadata = metadata or {}
        self.extra_opts = extra_opts
        self.ignore_global_cookies = ignore_global_cookies
        self.playlist_count_callback = None  # 可由 GUI 设置，用于通知播放列表项目数
        self.translator = None # 可由 GUI 设置
    
    def _t(self, key, default, *args):
        if self.translator: return self.translator(key).format(*args)
        return default.format(*args)

    def run(self) -> tuple[str, str]:
        """执行下载，返回 (filename, status) status: success, partial, error"""
        # 确保 translator 进入 extra_opts 以供 standalone 函数使用
        if self.extra_opts is None:
            self.extra_opts = {}
        if self.translator and "translator" not in self.extra_opts:
            self.extra_opts["translator"] = self.translator

        # 判断如果是普通静态文件，则走 requests 直接下载
        ext = self.url.split('?')[0].split('.')[-1].lower()
        if ext in ['pdf', 'txt', 'zip', 'csv', 'json']:
            sess = build_session(self.cookies or {}, self.referer)
            hooks = self.extra_opts.get("progress_hooks") if self.extra_opts else None
            success = download_with_requests(
                url=self.url,
                output_dir=self.output_dir,
                filename=self.filename,
                ext=ext,
                session=sess,
                progress_hooks=hooks,
                extra_opts=self.extra_opts,
            )
        else:
            success = download_with_ytdlp(
                url=self.url,
                output_dir=self.output_dir,
                filename=self.filename,
                cookies=self.cookies,
                cookie_domain=self.cookie_domain,
                referer=self.referer,
                extra_opts=self.extra_opts,
                playlist_count_callback=self.playlist_count_callback,
            )
        return self.filename, success

    def __repr__(self) -> str:
        return f"DownloadTask({self.filename!r}, url={self.url!r})"
