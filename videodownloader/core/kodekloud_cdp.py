#!/usr/bin/env python3
"""通过 Chrome/Edge DevTools Protocol 提取 KodeKloud 的 HttpOnly session-cookie。"""

from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

log = logging.getLogger("videodownloader")

# 供 PyInstaller 收集依赖（实际调用处仍有容错 import）
try:
    import websocket  # noqa: F401
except ImportError:
    websocket = None  # type: ignore

CDP_PORT_DEFAULT = 9223
TOKEN_COOKIE_NAMES = ("session-cookie",)
DEFAULT_START_URL = "https://learn.kodekloud.com/learn/courses"


def normalize_kodekloud_start_url(url: Optional[str]) -> str:
    """优先使用用户填写的课程地址；否则回退到课程列表页。"""
    u = (url or "").strip()
    if not u:
        return DEFAULT_START_URL
    low = u.lower()
    if "kodekloud.com" in low:
        # 去掉仅用于播放器的无关 hash，保留课程 path
        if "#" in u and "/courses/" in low:
            u = u.split("#", 1)[0]
        return u.rstrip("/") or DEFAULT_START_URL
    return DEFAULT_START_URL


def _cdp_navigate(port: int, url: str) -> None:
    """通过已有 CDP 将当前标签导航到指定课程页。"""
    try:
        from websocket import create_connection  # type: ignore
    except ImportError:
        return

    ws_url = None
    try:
        tabs = _cdp_http_json(f"http://127.0.0.1:{port}/json/list")
        for tab in tabs:
            if tab.get("type") == "page" and tab.get("webSocketDebuggerUrl"):
                ws_url = tab["webSocketDebuggerUrl"]
                break
        if not ws_url:
            version = _cdp_http_json(f"http://127.0.0.1:{port}/json/version")
            ws_url = version.get("webSocketDebuggerUrl")
    except Exception:
        return
    if not ws_url:
        return

    try:
        try:
            ws = create_connection(ws_url, timeout=10, suppress_origin=True)
        except TypeError:
            ws = create_connection(ws_url, timeout=10)
        try:
            mid = 1
            ws.send(json.dumps({"id": mid, "method": "Page.enable"}))
            _cdp_recv_result(ws, mid, timeout=5)
            mid = 2
            ws.send(json.dumps({"id": mid, "method": "Page.navigate", "params": {"url": url}}))
            _cdp_recv_result(ws, mid, timeout=15)
            log.info("CDP 已导航到: %s", url)
            time.sleep(2)
        finally:
            ws.close()
    except Exception as e:
        log.warning("CDP 导航失败（忽略）: %s", e)


def _browser_candidates() -> list[tuple[str, Path]]:
    system = platform.system()
    out: list[tuple[str, Path]] = []
    if system == "Windows":
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        pf = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        pf86 = Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        out.extend(
            [
                ("brave", local / "BraveSoftware/Brave-Browser/Application/brave.exe"),
                ("brave", pf / "BraveSoftware/Brave-Browser/Application/brave.exe"),
                ("brave", pf86 / "BraveSoftware/Brave-Browser/Application/brave.exe"),
                ("edge", local / "Microsoft/Edge/Application/msedge.exe"),
                ("edge", pf / "Microsoft/Edge/Application/msedge.exe"),
                ("edge", pf86 / "Microsoft/Edge/Application/msedge.exe"),
                ("chrome", local / "Google/Chrome/Application/chrome.exe"),
                ("chrome", pf / "Google/Chrome/Application/chrome.exe"),
                ("chrome", pf86 / "Google/Chrome/Application/chrome.exe"),
            ]
        )
    elif system == "Darwin":
        out.extend(
            [
                ("brave", Path("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")),
                ("chrome", Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")),
                ("edge", Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")),
            ]
        )
    else:
        out.extend(
            [
                ("brave", Path("/usr/bin/brave-browser")),
                ("brave", Path("/usr/bin/brave")),
                ("chrome", Path("/usr/bin/google-chrome")),
                ("chrome", Path("/usr/bin/chromium")),
                ("chrome", Path("/usr/bin/chromium-browser")),
                ("edge", Path("/usr/bin/microsoft-edge")),
            ]
        )
    seen = set()
    uniq: list[tuple[str, Path]] = []
    for name, path in out:
        key = str(path)
        if key in seen or not path.exists():
            continue
        seen.add(key)
        uniq.append((name, path))
    return uniq


def _cdp_http_json(url: str, timeout: float = 3.0):
    req = urllib.request.Request(url, headers={"User-Agent": "VideoDownloader"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _pick_ws_url(port: int) -> Optional[str]:
    try:
        version = _cdp_http_json(f"http://127.0.0.1:{port}/json/version")
        ws = version.get("webSocketDebuggerUrl")
        if ws:
            return ws
    except Exception:
        pass
    try:
        tabs = _cdp_http_json(f"http://127.0.0.1:{port}/json/list")
        for tab in tabs:
            if tab.get("type") == "page" and tab.get("webSocketDebuggerUrl"):
                return tab["webSocketDebuggerUrl"]
            if tab.get("webSocketDebuggerUrl"):
                return tab["webSocketDebuggerUrl"]
    except Exception:
        return None
    return None


def _cdp_recv_result(ws, msg_id: int, timeout: float = 10) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        raw = ws.recv()
        data = json.loads(raw)
        if data.get("id") != msg_id:
            continue
        if "error" in data:
            err = data["error"]
            raise RuntimeError(err if isinstance(err, str) else json.dumps(err, ensure_ascii=False))
        return data.get("result") or {}
    raise RuntimeError(f"CDP 请求超时 (id={msg_id})")


def _cdp_get_all_cookies(ws_url: str) -> list[dict]:
    try:
        from websocket import create_connection  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "缺少依赖 websocket-client。请先执行: pip install websocket-client"
        ) from e

    try:
        ws = create_connection(ws_url, timeout=10, suppress_origin=True)
    except TypeError:
        # 旧版 websocket-client 无 suppress_origin
        ws = create_connection(ws_url, timeout=10)
    except Exception as e:
        raise RuntimeError(
            f"无法连接浏览器 WebSocket（常见原因：缺少 --remote-allow-origins=*）: {e}"
        ) from e

    try:
        msg_id = 1
        ws.send(json.dumps({"id": msg_id, "method": "Network.enable"}))
        _cdp_recv_result(ws, msg_id, timeout=5)

        msg_id = 2
        ws.send(json.dumps({"id": msg_id, "method": "Network.getAllCookies"}))
        result = _cdp_recv_result(ws, msg_id, timeout=10)
        cookies = list(result.get("cookies") or [])
        if cookies:
            return cookies

        # 部分 Chromium 版本浏览器级 getAllCookies 为空，再试 Storage.getCookies
        msg_id = 3
        ws.send(json.dumps({"id": msg_id, "method": "Storage.getCookies"}))
        try:
            result = _cdp_recv_result(ws, msg_id, timeout=10)
            return list(result.get("cookies") or [])
        except RuntimeError:
            return cookies
    finally:
        try:
            ws.close()
        except Exception:
            pass


def _token_from_cookies(cookies: list[dict]) -> Optional[str]:
    # Prefer session-cookie on kodekloud domains
    ranked: list[tuple[int, str]] = []
    for c in cookies:
        name = str(c.get("name") or "")
        domain = str(c.get("domain") or "")
        value = str(c.get("value") or "")
        if "kodekloud" not in domain.lower():
            continue
        if name in TOKEN_COOKIE_NAMES and value.count(".") == 2 and value.startswith("eyJ"):
            ranked.append((0, value))
        elif name.lower() == "session-cookie" and value:
            ranked.append((1, value))
    ranked.sort(key=lambda x: x[0])
    return ranked[0][1] if ranked else None


_EXE_NAMES = {
    "brave": ("brave.exe",),
    "chrome": ("chrome.exe",),
    "edge": ("msedge.exe",),
}

_USER_DATA_REL = {
    "brave": ("LOCALAPPDATA", "BraveSoftware/Brave-Browser/User Data"),
    "chrome": ("LOCALAPPDATA", "Google/Chrome/User Data"),
    "edge": ("LOCALAPPDATA", "Microsoft/Edge/User Data"),
}


def is_browser_running(browser: str = "brave") -> bool:
    """检测 Chromium 系浏览器进程是否仍在运行（含托盘驻留）。"""
    names = _EXE_NAMES.get(browser.lower(), (f"{browser.lower()}.exe",))
    system = platform.system()
    if system == "Windows":
        for exe in names:
            try:
                r = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {exe}", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                out = (r.stdout or "").strip().lower()
                if not out or "no tasks" in out or "没有" in out:
                    continue
                if exe.lower() in out:
                    return True
            except Exception:
                continue
        return False
    # Linux / macOS
    for exe in names:
        try:
            r = subprocess.run(["pgrep", "-x", exe.replace(".exe", "")], capture_output=True)
            if r.returncode == 0:
                return True
        except Exception:
            pass
    return False


def _user_data_dir(browser: str) -> Optional[Path]:
    meta = _USER_DATA_REL.get(browser.lower())
    if not meta:
        return None
    env, rel = meta
    base = os.environ.get(env, "")
    if not base:
        return None
    p = Path(base) / rel
    return p if p.is_dir() else None


def _profile_dirs(user_data: Path) -> list[str]:
    names: list[str] = []
    for name in ("Default", "Profile 1", "Profile 2", "Profile 3"):
        if (user_data / name).is_dir():
            names.append(name)
    for p in sorted(user_data.glob("Profile *")):
        if p.is_dir() and p.name not in names:
            names.append(p.name)
    return names or ["Default"]


def launch_browser_with_cdp(
    port: int = CDP_PORT_DEFAULT,
    start_url: Optional[str] = None,
) -> tuple[Optional[subprocess.Popen], Optional[str]]:
    """启动带远程调试的临时配置浏览器并打开 KodeKloud。返回 (proc, browser_name)。"""
    candidates = _browser_candidates()
    if not candidates:
        return None, None

    open_url = normalize_kodekloud_start_url(start_url)
    profile = Path(os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp") / f"vd-kk-cdp-{port}"
    profile.mkdir(parents=True, exist_ok=True)

    for name, exe in candidates:
        cmd = [
            str(exe),
            f"--remote-debugging-port={port}",
            "--remote-allow-origins=*",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            open_url,
        ]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for _ in range(20):
                time.sleep(0.5)
                if _pick_ws_url(port):
                    log.info("已启动 %s (临时配置, CDP port %s) → %s", name, port, open_url)
                    try:
                        _cdp_navigate(port, open_url)
                    except Exception:
                        pass
                    return proc, name
            proc.terminate()
        except Exception as e:
            log.warning("启动 %s 失败: %s", name, e)
    return None, None


def launch_browser_with_user_profile(
    browser: str = "brave",
    port: int = CDP_PORT_DEFAULT,
    profile_directory: Optional[str] = None,
    start_url: Optional[str] = None,
) -> tuple[Optional[subprocess.Popen], Optional[str]]:
    """
    用「真实 User Data」启动浏览器 + CDP，从而读到已登录的 HttpOnly session-cookie。
    要求：该浏览器进程必须已完全退出，否则会因 SingletonLock / 文件占用失败。
    """
    browser = browser.lower()
    open_url = normalize_kodekloud_start_url(start_url)
    if is_browser_running(browser):
        raise RuntimeError(
            f"{browser} 仍在运行，无法读取已登录配置。\n"
            "请完全退出（托盘图标右键 → 退出），确认任务管理器无 brave.exe 后再重试。"
        )

    user_data = _user_data_dir(browser)
    if not user_data:
        raise RuntimeError(f"未找到 {browser} 的 User Data 目录")

    candidates = [(n, p) for n, p in _browser_candidates() if n == browser]
    if not candidates:
        raise RuntimeError(f"未找到 {browser} 可执行文件")

    profiles = [profile_directory] if profile_directory else _profile_dirs(user_data)
    exe_name, exe = candidates[0]

    for prof in profiles:
        cmd = [
            str(exe),
            f"--remote-debugging-port={port}",
            "--remote-allow-origins=*",
            f"--user-data-dir={user_data}",
            f"--profile-directory={prof}",
            "--no-first-run",
            "--no-default-browser-check",
            open_url,
        ]
        try:
            log.info("尝试用真实配置启动 %s (profile=%s, CDP=%s) → %s", exe_name, prof, port, open_url)
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for _ in range(30):
                time.sleep(0.5)
                if _pick_ws_url(port):
                    log.info("已启动 %s 真实配置 profile=%s", exe_name, prof)
                    try:
                        _cdp_navigate(port, open_url)
                    except Exception:
                        pass
                    return proc, exe_name
            try:
                proc.terminate()
            except Exception:
                pass
        except Exception as e:
            log.warning("启动 %s profile=%s 失败: %s", exe_name, prof, e)

    raise RuntimeError(
        f"无法用真实配置启动 {browser}。\n"
        "请确认已完全退出浏览器后重试；或改用「KodeKloud 自动提取 Token」临时窗口登录。"
    )


def _terminate_browser_tree(proc: Optional[subprocess.Popen]) -> None:
    if proc is None:
        return
    try:
        if platform.system() == "Windows" and proc.pid:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
                timeout=15,
            )
        else:
            proc.terminate()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _poll_token(ws_url: str, wait_login_seconds: int, port: int = CDP_PORT_DEFAULT) -> str:
    deadline = time.time() + max(2, wait_login_seconds)
    last_names: list[str] = []
    last_err: Optional[Exception] = None
    while time.time() < deadline:
        try:
            cookies = _cdp_get_all_cookies(ws_url)
            last_err = None
        except Exception as e:
            last_err = e
            log.warning("CDP 读取 Cookie 暂失败，重试中: %s", e)
            time.sleep(1.5)
            refreshed = _pick_ws_url(port) or ws_url
            ws_url = refreshed
            continue
        kk = [c for c in cookies if "kodekloud" in str(c.get("domain") or "").lower()]
        last_names = sorted({str(c.get("name")) for c in kk})
        if last_names:
            log.info("CDP 可见 kodekloud Cookie: %s", ", ".join(last_names))
        token = _token_from_cookies(cookies)
        if token:
            log.info("已通过 CDP 提取到 session-cookie")
            return token
        time.sleep(1.5)

    extra = f"\n最后一次 CDP 错误: {last_err}" if last_err else ""
    raise RuntimeError(
        "浏览器中未找到 HttpOnly Cookie「session-cookie」。\n"
        "请确认已在打开的窗口登录 learn.kodekloud.com，并能正常播放课程视频。\n"
        f"当前 kodekloud 相关 Cookie: {', '.join(last_names) or '(无)'}"
        f"{extra}\n\n"
        "手动备选：F12 → Application/应用程序 → Cookies → learn.kodekloud.com\n"
        "复制 session-cookie 的值，用「剪贴板」粘贴。"
    )


def extract_kodekloud_from_user_profile(
    browser: str = "brave",
    port: int = CDP_PORT_DEFAULT,
    wait_seconds: int = 12,
    close_after: bool = True,
    start_url: Optional[str] = None,
) -> str:
    """关闭浏览器后，用真实配置 + CDP 提取 session-cookie（推荐给「Brave 浏览器」选项）。"""
    open_url = normalize_kodekloud_start_url(start_url)
    user_data = _user_data_dir(browser)
    profiles = _profile_dirs(user_data) if user_data else ["Default"]
    errors: list[str] = []

    # 若已有调试端口（用户手动开过），先导航到课程页再读
    ws_url = _pick_ws_url(port)
    if ws_url:
        try:
            _cdp_navigate(port, open_url)
            return _poll_token(ws_url, wait_seconds, port=port)
        except Exception as e:
            log.warning("已有 CDP 端口但提取失败，将重启浏览器配置重试: %s", e)

    per_profile_wait = max(6, wait_seconds // max(1, len(profiles)))
    for prof in profiles:
        proc = None
        try:
            # 上一轮残留进程会挡 SingletonLock
            if is_browser_running(browser):
                log.warning("%s 仍在运行，尝试结束残留进程…", browser)
                if platform.system() == "Windows":
                    for exe in _EXE_NAMES.get(browser, ()):
                        subprocess.run(
                            ["taskkill", "/IM", exe, "/F"],
                            capture_output=True,
                            timeout=15,
                        )
                time.sleep(2)
            proc, _ = launch_browser_with_user_profile(
                browser=browser,
                port=port,
                profile_directory=prof,
                start_url=open_url,
            )
            time.sleep(2)  # 等配置与 Cookie 落盘就绪
            ws_url = _pick_ws_url(port)
            if not ws_url:
                raise RuntimeError(f"无法连接 CDP 127.0.0.1:{port} (profile={prof})")
            return _poll_token(ws_url, per_profile_wait, port=port)
        except Exception as e:
            errors.append(f"{prof}: {e}")
            log.warning("profile=%s 提取失败: %s", prof, e)
        finally:
            if close_after:
                _terminate_browser_tree(proc)
            time.sleep(1.5)

    raise RuntimeError(
        "未能从任何 Brave 配置提取 session-cookie。\n"
        + "\n".join(errors)
        + "\n\n若登录在「Profile 1」等配置中，请确认该配置曾打开过课程页。"
    )


def extract_kodekloud_session_token(
    port: int = CDP_PORT_DEFAULT,
    auto_launch: bool = True,
    wait_login_seconds: int = 5,
    prefer_user_profile: bool = False,
    browser: str = "brave",
    start_url: Optional[str] = None,
) -> Optional[str]:
    """
    从 CDP 提取 session-cookie。

    prefer_user_profile=True：优先用真实 Brave/Chrome 配置（需先完全退出浏览器）。
    auto_launch=True：无调试端口时拉起临时浏览器窗口。
    """
    open_url = normalize_kodekloud_start_url(start_url)
    if prefer_user_profile:
        try:
            return extract_kodekloud_from_user_profile(
                browser=browser,
                port=port,
                wait_seconds=wait_login_seconds,
                close_after=True,
                start_url=open_url,
            )
        except RuntimeError as e:
            log.warning("真实配置提取失败，回退临时窗口: %s", e)

    ws_url = _pick_ws_url(port)
    if not ws_url and auto_launch:
        proc, _ = launch_browser_with_cdp(port, start_url=open_url)
        if proc is None:
            raise RuntimeError("未能启动 Brave/Edge/Chrome。请确认已安装 Brave 浏览器。")
        ws_url = _pick_ws_url(port)

    if not ws_url:
        raise RuntimeError(
            f"无法连接浏览器 CDP (127.0.0.1:{port})。\n"
            "请手动用调试模式启动 Brave，例如:\n"
            f'  brave.exe --remote-debugging-port={port} --remote-allow-origins=* --user-data-dir="%TEMP%\\vd-kk"\n'
            "然后登录 learn.kodekloud.com 后重试。"
        )

    try:
        _cdp_navigate(port, open_url)
    except Exception:
        pass
    return _poll_token(ws_url, wait_login_seconds, port=port)
