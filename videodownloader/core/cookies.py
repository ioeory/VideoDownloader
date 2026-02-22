#!/usr/bin/env python3
"""
通用 Cookie 管理模块
支持：Netscape 文件 / 手动字符串 / 浏览器自动提取（含 WSL）
"""

import base64
import json
import logging
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from videodownloader.core.utils import get_windows_username, is_wsl

log = logging.getLogger("videodownloader")

# Windows 浏览器 Cookie 路径映射
_WIN_BROWSER_COOKIE_PATHS = {
    "brave":    "AppData/Local/BraveSoftware/Brave-Browser/User Data",
    "chrome":   "AppData/Local/Google/Chrome/User Data",
    "edge":     "AppData/Local/Microsoft/Edge/User Data",
    "vivaldi":  "AppData/Local/Vivaldi/User Data",
    "opera":    "AppData/Roaming/Opera Software/Opera Stable",
    "chromium": "AppData/Local/Chromium/User Data",
}


# ─────────────────────────────────────────────
# Netscape Cookie 文件
# ─────────────────────────────────────────────

def load_netscape_cookie_file(filepath: str, domain_filter: Optional[str] = None) -> dict:
    """
    解析 Netscape 格式 cookies.txt 文件。
    domain_filter: 若指定，只保留含该字符串的域名 Cookie（如 'deeplearning.ai'）
    """
    cookies: dict = {}
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Cookie 文件不存在: {filepath}")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                domain, _, _, _, _, name, value = parts[:7]
                # 域名过滤逻辑：如果 filter 是 domain 的子串，或者 domain 是 filter 的子串 (支持 .kodekloud.com)
                if domain_filter:
                    clean_domain = domain.lstrip(".")
                    clean_filter = domain_filter.lstrip(".")
                    if clean_filter not in clean_domain and clean_domain not in clean_filter:
                        continue
                cookies[name] = value

    if not cookies:
        log.warning(f"Cookie 文件中未找到匹配的 Cookie: {filepath} (filter={domain_filter})")
    else:
        log.info(f"从 {filepath} 加载 {len(cookies)} 个 Cookie")
    return cookies


def write_netscape_cookies(cookies: dict, filepath: Path, domain: str = ".example.com") -> None:
    """将 Cookie dict 写入 Netscape 格式文件（供 yt-dlp 使用）"""
    lines = ["# Netscape HTTP Cookie File\n"]
    for name, value in cookies.items():
        lines.append(f"{domain}\tTRUE\t/\tFALSE\t2147483647\t{name}\t{value}\n")
    filepath.write_text("".join(lines))


# ─────────────────────────────────────────────
# 手动字符串解析
# ─────────────────────────────────────────────

def parse_cookie_string(cookie_str: str) -> dict:
    """解析手动提供的 Cookie 字符串，格式: key1=val1; key2=val2"""
    cookie_str = cookie_str.strip()
    
    # 用户有可能直接粘贴了一串 JWT 或者 Base64 token，而不是完整的 key=value 形式
    if ";" not in cookie_str:
        if "=" not in cookie_str or cookie_str.index("=") > len(cookie_str) - 3:
            # 没有等号，或等号只出现在末尾（Base64 padding）
            return {"__raw_token__": cookie_str}

    cookies: dict = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
            
    # 如果解析出来只有 1 个，并且 value 为空，极大概率也是误将带 padding 的 token 当做 key
    if len(cookies) == 1:
        k, v = list(cookies.items())[0]
        if not v and len(k) > 20:
            return {"__raw_token__": cookie_str}
            
    return cookies


# ─────────────────────────────────────────────
# WSL 专用：读取 Windows 浏览器 Cookie
# ─────────────────────────────────────────────

def _decrypt_windows_cookie_value(encrypted_value: bytes, local_state_path: Path) -> Optional[str]:
    """
    通过 PowerShell 调用 Windows DPAPI 解密 Chrome 系浏览器 Cookie 值。
    Chrome v80+ 使用 AES-256-GCM，密钥存在 Local State 文件中，由 DPAPI 加密。
    """
    if not encrypted_value:
        return None

    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            local_state = json.load(f)
        encrypted_key_b64 = local_state.get("os_crypt", {}).get("encrypted_key", "")
        if not encrypted_key_b64:
            return None
        encrypted_key = base64.b64decode(encrypted_key_b64)[5:]  # 跳过 "DPAPI" 前缀
    except Exception:
        return None

    key_b64 = base64.b64encode(encrypted_key).decode()
    ps_cmd = (
        f"$bytes = [Convert]::FromBase64String('{key_b64}'); "
        "$decrypted = [System.Security.Cryptography.ProtectedData]::Unprotect("
        "$bytes, $null, [System.Security.Cryptography.DataProtectionScope]::CurrentUser); "
        "[Convert]::ToBase64String($decrypted)"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        aes_key = base64.b64decode(result.stdout.strip())
    except Exception:
        return None

    try:
        from Cryptodome.Cipher import AES  # type: ignore
        if encrypted_value[:3] != b"v10":
            return None
        iv = encrypted_value[3:15]
        payload = encrypted_value[15:]
        cipher = AES.new(aes_key, AES.MODE_GCM, nonce=iv)
        decrypted = cipher.decrypt(payload[:-16])
        return decrypted.decode("utf-8", errors="ignore")
    except ImportError:
        log.warning("pycryptodomex 未安装，无法解密 Cookie。运行: pip install pycryptodomex")
        return None
    except Exception:
        return None


def get_wsl_browser_cookies(browser: str, domain_filter: Optional[str] = None) -> dict:
    """
    WSL 专用：直接读取 Windows 浏览器 Cookie SQLite 数据库。
    支持 Chrome 系浏览器（Brave、Chrome、Edge 等）。
    """
    win_user = get_windows_username()
    if not win_user:
        raise RuntimeError("无法确定 Windows 用户名")

    rel_path = _WIN_BROWSER_COOKIE_PATHS.get(browser.lower())
    if not rel_path:
        raise ValueError(f"WSL 模式不支持浏览器: {browser}")

    user_data_dir = Path(f"/mnt/c/Users/{win_user}/{rel_path}")
    if not user_data_dir.exists():
        raise FileNotFoundError(f"浏览器数据目录不存在: {user_data_dir}")

    # 查找 Cookie 文件
    cookie_db_path = None
    for profile in ["Default", "Profile 1"]:
        for sub in ["Network/Cookies", "Cookies"]:
            p = user_data_dir / profile / sub
            if p.exists():
                cookie_db_path = p
                break
        if cookie_db_path:
            break

    if not cookie_db_path:
        raise FileNotFoundError(f"未找到 Cookie 文件，路径: {user_data_dir}")

    local_state_path = user_data_dir / "Local State"
    log.info(f"读取 Cookie 数据库: {cookie_db_path}")

    # 复制 Cookie 文件（浏览器运行时被锁定，需 PowerShell 复制）
    win_temp_dir = Path("/mnt/c/Windows/Temp")
    tmp_win_path = win_temp_dir / "vd_cookies_tmp.db"
    tmp_path = None
    try:
        win_cookie_path = str(cookie_db_path).replace("/mnt/c/", "C:\\").replace("/", "\\")
        win_tmp_path_str = str(tmp_win_path).replace("/mnt/c/", "C:\\").replace("/", "\\")
        ps_copy_cmd = f"Copy-Item -Path '{win_cookie_path}' -Destination '{win_tmp_path_str}' -Force"
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_copy_cmd],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            raise PermissionError(
                f"PowerShell 复制 Cookie 文件失败: {result.stderr.strip()}\n"
                "  提示: 关闭浏览器后重试，或使用 --cookies-file 参数"
            )
        copy_target = tmp_win_path
    except FileNotFoundError:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path_obj = Path(tmp.name)
        shutil.copy2(str(cookie_db_path), str(tmp_path_obj))
        copy_target = tmp_path_obj
        tmp_path = tmp_path_obj

    try:
        conn = sqlite3.connect(str(copy_target))
        cursor = conn.cursor()
        if domain_filter:
            cursor.execute(
                "SELECT name, value, encrypted_value FROM cookies WHERE host_key LIKE ?",
                (f"%{domain_filter}%",),
            )
        else:
            cursor.execute("SELECT name, value, encrypted_value FROM cookies")
        rows = cursor.fetchall()
        conn.close()
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        if tmp_win_path.exists():
            try:
                tmp_win_path.unlink()
            except Exception:
                pass

    cookies: dict = {}
    for name, value, encrypted_value in rows:
        if value:
            cookies[name] = value
        elif encrypted_value:
            decrypted = _decrypt_windows_cookie_value(encrypted_value, local_state_path)
            if decrypted:
                cookies[name] = decrypted

    log.info(f"从 WSL Windows {browser} 获取到 {len(cookies)} 个 Cookie")
    return cookies


# ─────────────────────────────────────────────
# 统一 Cookie 管理器
# ─────────────────────────────────────────────

class CookieManager:
    """
    统一 Cookie 管理器
    优先级: cookies_file > cookie_str > 浏览器自动提取
    """

    SUPPORTED_BROWSERS = ["chrome", "chromium", "firefox", "edge", "brave", "safari", "opera", "vivaldi"]

    def __init__(
        self,
        cookies_file: Optional[str] = None,
        cookie_str: Optional[str] = None,
        browser: str = "chrome",
        domain_filter: Optional[str] = None,
    ):
        self.cookies_file = cookies_file
        self.cookie_str = cookie_str
        self.browser = browser
        self.domain_filter = domain_filter

    def get(self) -> dict:
        """获取 Cookie 字典"""
        if self.cookies_file:
            return load_netscape_cookie_file(self.cookies_file, self.domain_filter)
        if self.cookie_str:
            cookies = parse_cookie_string(self.cookie_str)
            log.info(f"使用手动提供的 Cookie ({len(cookies)} 个)")
            return cookies
        return self._from_browser()

    def _from_browser(self) -> dict:
        """从浏览器提取 Cookie"""
        if is_wsl():
            log.info(f"检测到 WSL 环境，尝试读取 Windows {self.browser} Cookie 数据库...")
            try:
                cookies = get_wsl_browser_cookies(self.browser, self.domain_filter)
                if cookies:
                    return cookies
            except FileNotFoundError as e:
                log.warning(f"WSL 直接读取失败: {e}")
            except Exception as e:
                log.warning(f"WSL Cookie 读取异常: {e}")
            log.warning(
                "WSL 自动提取 Cookie 失败！\n"
                "请使用以下方法导出 Cookie 后重试:\n"
                "  1. 安装扩展「Get cookies.txt LOCALLY」\n"
                "     https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc\n"
                "  2. 访问目标网站，点击扩展图标导出 cookies.txt\n"
                "  3. 运行: python main.py ... --cookies-file cookies.txt"
            )
            raise RuntimeError("WSL 自动提取 Cookie 失败")

        # 非 WSL：使用 browser_cookie3
        try:
            import browser_cookie3  # type: ignore

            browser_map = {
                "chrome":   browser_cookie3.chrome,
                "chromium": browser_cookie3.chromium,
                "firefox":  browser_cookie3.firefox,
                "edge":     browser_cookie3.edge,
                "brave":    browser_cookie3.brave,
                "safari":   browser_cookie3.safari,
                "opera":    browser_cookie3.opera,
                "vivaldi":  browser_cookie3.vivaldi,
            }
            loader = browser_map.get(self.browser.lower())
            if not loader:
                raise ValueError(f"不支持的浏览器: {self.browser}")

            domain = self.domain_filter or ""
            jar = loader(domain_name=f".{domain}" if domain else "")
            cookies = {c.name: c.value for c in jar}
            if not cookies:
                raise RuntimeError(f"未找到 Cookie，请先在该浏览器中登录目标网站")
            log.info(f"成功从 {self.browser} 获取 {len(cookies)} 个 Cookie")
            return cookies
        except ImportError:
            raise RuntimeError("请先安装 browser-cookie3 以支持此浏览器: pip install browser-cookie3")
