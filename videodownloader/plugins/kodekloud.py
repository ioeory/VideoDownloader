import base64
import json
import logging
import re
import time
from pathlib import Path
from typing import List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from videodownloader.core.downloader import DownloadTask
from videodownloader.core.utils import HAS_FFMPEG, sanitize_filename
from videodownloader.plugins.base import BasePlugin

log = logging.getLogger("videodownloader")

class KodeKloudPlugin(BasePlugin):
    name = "kodekloud"
    description = "KodeKloud 课程下载 (learn.kodekloud.com)"
    domains = ["learn.kodekloud.com", "kodekloud.com"]

    _LESSON_TIMEOUT = 30
    _LESSON_RETRIES = 4
    _LESSON_GAP_SEC = 0.35

    def can_handle(self, url: str) -> bool:
        return any(domain in url for domain in self.domains)

    def get_cookies_domain(self) -> str:
        return "learn.kodekloud.com"

    # 课时 API 需要 KodeKloud 签发的 session-cookie，或 Firebase ID Token。
    # `_secure-user-session` 是 Firebase Session Cookie，issuer 不被 learn-api 接受。
    _TOKEN_COOKIE_NAMES = (
        "session-cookie",
        "secure-user-session",
        "_secure-user-session",  # 仅作最后兜底；通常会因 issuer 被拒
    )

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=2,
            connect=2,
            read=0,  # 课时级重试自己做，避免与业务重试叠加过猛
            status=0,
            backoff_factor=0.5,
            allowed_methods=frozenset(["GET", "HEAD"]),
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=4)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _get_json_with_retry(
        self,
        session: requests.Session,
        url: str,
        *,
        headers: dict,
        params: Optional[dict] = None,
        timeout: int = 30,
        retries: int = 4,
        **kwargs,
    ) -> requests.Response:
        """GET JSON，对超时 / 5xx / 429 做退避重试。"""
        last_exc: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            if kwargs.get("stop_check") and kwargs["stop_check"]():
                raise RuntimeError("aborted")
            try:
                resp = session.get(url, headers=headers, params=params, timeout=timeout)
                if resp.status_code == 401:
                    return resp
                if resp.status_code in (429, 500, 502, 503, 504):
                    wait = min(8.0, 0.8 * (2 ** (attempt - 1)))
                    log.warning(self._t(
                        "log_kk_lesson_retry",
                        "⚠️ Lesson API HTTP {} (attempt {}/{}), retry in {:.1f}s...",
                        resp.status_code, attempt, retries, wait,
                        **kwargs,
                    ))
                    time.sleep(wait)
                    last_exc = requests.HTTPError(
                        f"{resp.status_code} for url: {resp.url}", response=resp
                    )
                    continue
                return resp
            except (requests.Timeout, requests.ConnectionError) as e:
                wait = min(8.0, 0.8 * (2 ** (attempt - 1)))
                log.warning(self._t(
                    "log_kk_lesson_retry_net",
                    "⚠️ Lesson API network error (attempt {}/{}): {}; retry in {:.1f}s...",
                    attempt, retries, e, wait,
                    **kwargs,
                ))
                time.sleep(wait)
                last_exc = e
        if last_exc:
            raise last_exc
        raise RuntimeError("lesson request failed")

    @staticmethod
    def _normalize_token(token: str) -> str:
        token = (token or "").strip().strip('"').strip("'")
        lowered = token.lower()
        for prefix in ("authorization:", "bearer "):
            if lowered.startswith(prefix):
                token = token[len(prefix):].strip().strip('"').strip("'")
                lowered = token.lower()
        return token

    @staticmethod
    def _decode_jwt_payload(token: str) -> Optional[dict]:
        try:
            parts = token.split(".")
            if len(parts) < 2:
                return None
            payload = parts[1] + "=" * (-len(parts[1]) % 4)
            return json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))
        except Exception:
            return None

    @classmethod
    def _decode_jwt_header(cls, token: str) -> Optional[dict]:
        try:
            parts = token.split(".")
            if len(parts) < 2:
                return None
            header = parts[0] + "=" * (-len(parts[0]) % 4)
            return json.loads(base64.urlsafe_b64decode(header.encode("utf-8")))
        except Exception:
            return None

    @classmethod
    def _token_usable_for_api(cls, token: str) -> bool:
        """必须是可解码 JWT，且不能是 Firebase Session Cookie。"""
        token = cls._normalize_token(token)
        if not token or token.count(".") != 2:
            return False
        if cls._decode_jwt_header(token) is None:
            return False
        payload = cls._decode_jwt_payload(token)
        if not payload:
            return False
        iss = str(payload.get("iss") or "")
        if "session.firebase.google.com" in iss:
            return False
        return True

    def _get_token(self, cookies: dict) -> Optional[str]:
        """从 cookies 中获取可用于 learn-api 的鉴权 JWT。"""
        candidates: List[str] = []

        if "__raw_token__" in cookies:
            candidates.append(cookies["__raw_token__"])

        lower_map = {k.lower(): v for k, v in cookies.items()}
        for name in self._TOKEN_COOKIE_NAMES:
            token = lower_map.get(name.lower())
            if token:
                candidates.append(token)

        # 兜底：任意看起来像 JWT 的长 Cookie
        for key, val in cookies.items():
            if key.startswith("__"):
                continue
            if (
                isinstance(val, str)
                and val.count(".") >= 2
                and len(val) > 100
            ):
                candidates.append(val)

        seen = set()
        invalid_jwt_seen = False
        for token in candidates:
            token = self._normalize_token(token)
            if not token or token in seen:
                continue
            seen.add(token)
            if self._token_usable_for_api(token):
                return token
            payload = self._decode_jwt_payload(token) or {}
            iss = str(payload.get("iss") or "")
            if "session.firebase.google.com" in iss:
                cookies["__rejected_firebase_session__"] = "1"
            elif token.count(".") == 2:
                invalid_jwt_seen = True

        if invalid_jwt_seen:
            cookies["__invalid_jwt__"] = "1"
        return None

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
            if cookies.pop("__rejected_firebase_session__", None):
                log.error(self._t(
                    "log_kk_wrong_token",
                    "🚫 Found '_secure-user-session' (Firebase Session Cookie), but learn-api rejects its JWT issuer.\n"
                    "   How to get a working token:\n"
                    "   1) Open https://learn.kodekloud.com and play any lesson video\n"
                    "   2) F12 → Network → filter 'lessons' → open the learn-api request\n"
                    "   3) Copy ONLY the token after 'Bearer ' (starts with eyJ...)\n"
                    "   4) In this app, choose Clipboard and paste that JWT\n"
                    "   Or: DevTools → Application → Cookies → copy 'session-cookie' if present",
                    **kwargs,
                ))
            elif cookies.pop("__invalid_jwt__", None):
                log.error(self._t(
                    "log_kk_invalid_jwt",
                    "🚫 The pasted token is not a valid JWT (header is not JSON).\n"
                    "   Please paste ONLY the raw token starting with eyJ... (three segments separated by dots).\n"
                    "   Do not include 'Bearer ', 'Authorization:', quotes, or cookie names.",
                    **kwargs,
                ))
            else:
                log.error(self._t(
                    "log_session_cookie_missing",
                    "🚫 Missing auth token cookie ('session-cookie') or paste a Bearer JWT via Clipboard.",
                    **kwargs,
                ))
            return []

        # 提取 course slug 和 lesson_id (可选)
        # 支持:
        #   - 课程页: https://learn.kodekloud.com/user/courses/ai-assisted-ansible
        #   - 新版课程页: https://learn.kodekloud.com/learn/courses/gateway-api-...
        #   - 课时页: .../module/.../lesson/UUID
        course_slug = url_or_id
        lesson_id_filter = None
        
        if "kodekloud.com" in url_or_id:
            match = re.search(r'/(?:user|learn)/courses/([^/]+)', url_or_id)
            if match:
                course_slug = match.group(1)
            
            # 尝试捕获特定课时 ID
            lesson_match = re.search(r'/lesson/([^/?#]+)', url_or_id)
            if lesson_match:
                lesson_id_filter = lesson_match.group(1)
        else:
            # 兼容直接输入 slug 的情况
            course_slug = url_or_id.strip("/").split("/")[-1]
        log.info(self._t("log_fetching_course_info", "⏳ Fetching course info: {}", course_slug, **kwargs))

        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://learn.kodekloud.com/",
            "Origin": "https://learn.kodekloud.com",
        }

        session = self._build_session()

        # 1. 获取课程结构
        course_api = f"https://learn-api.kodekloud.com/api/courses/{course_slug}"
        try:
            r = self._get_json_with_retry(
                session, course_api, headers=headers, timeout=20, retries=3, **kwargs
            )
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
        failed_lessons = 0

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

                if lesson_id_filter and lesson_id != lesson_id_filter:
                    continue

                if lesson_type != "video":
                    log.debug(self._t("log_skipping_non_video", "⏭ Skipping non-video content: {}", lesson_title, **kwargs))
                    continue

                log.info(self._t("log_getting_lesson_video", "⏳ Getting video ID for lesson: {}", lesson_title, **kwargs))
                lesson_api = f"https://learn-api.kodekloud.com/api/lessons/{lesson_id}"
                try:
                    if tasks or failed_lessons:
                        time.sleep(self._LESSON_GAP_SEC)

                    lr = self._get_json_with_retry(
                        session,
                        lesson_api,
                        headers=headers,
                        params={"course_id": course_data.get("id")},
                        timeout=self._LESSON_TIMEOUT,
                        retries=self._LESSON_RETRIES,
                        **kwargs,
                    )
                    if lr.status_code == 401:
                        detail = ""
                        try:
                            detail = lr.json().get("message") or ""
                        except Exception:
                            detail = lr.text[:120]
                        log.error(self._t(
                            "log_lesson_unauthorized",
                            "❌ Lesson API 401 Unauthorized ({}). Token is invalid/expired or wrong type.\n"
                            "   Tip: paste the Authorization Bearer JWT from browser Network tab (Clipboard mode).",
                            detail or "unauthorized",
                            **kwargs,
                        ))
                        return tasks
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
                    failed_lessons += 1
                    log.error(self._t("log_lesson_failed", "❌ Failed for lesson {}: {}", lesson_title, e, **kwargs))

        if failed_lessons:
            log.warning(self._t(
                "log_kk_partial_lessons",
                "⚠️ {} lesson(s) failed while resolving video URLs; continuing with {} task(s).",
                failed_lessons, len(tasks),
                **kwargs,
            ))

        return tasks
