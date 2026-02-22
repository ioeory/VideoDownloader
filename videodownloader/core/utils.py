#!/usr/bin/env python3
"""
通用工具函数模块
"""

import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional


def setup_logging(verbose: bool = False, log_file: Optional[str] = "download.log") -> logging.Logger:
    """配置并返回根 Logger"""
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )
    return logging.getLogger("videodownloader")


def get_ffmpeg_path() -> Optional[str]:
    """获取 ffmpeg 可执行文件的路径，兼容自动安装的环境"""
    # 1. 系统 PATH 中寻找
    p = shutil.which("ffmpeg")
    if p:
        return p
    
    # 2. 从 install.bat 自动下载的路径寻找 (Windows LocalAppData)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base_dir = Path(local_app_data) / "VideoDownloader" / "ffmpeg"
        if base_dir.exists():
            for exe in base_dir.rglob("ffmpeg.exe"):
                if "bin" in str(exe):
                    return str(exe)
                    
    return None

FFMPEG_PATH = get_ffmpeg_path()
HAS_FFMPEG = FFMPEG_PATH is not None


def is_wsl() -> bool:
    """检测当前是否运行于 WSL 环境"""
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except FileNotFoundError:
        return False


def get_windows_username() -> Optional[str]:
    """获取 Windows 用户名（WSL 环境）"""
    users_dir = Path("/mnt/c/Users")
    if users_dir.exists():
        for d in users_dir.iterdir():
            if d.is_dir() and d.name not in ("All Users", "Default", "Default User", "Public"):
                return d.name
    return os.environ.get("USERNAME") or os.environ.get("USER")


def sanitize_filename(name: str) -> str:
    """将字符串中的非法文件名字符替换为下划线"""
    import re
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()


def ensure_dir(path: Path) -> Path:
    """确保目录存在，返回 Path 对象"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def file_is_complete(path: Path, expected_size: Optional[int] = None, min_size: int = 1024) -> bool:
    """
    判断文件是否已完整下载。
    如果有预期大小，则要求文件大小必须等于预期大小才算完整；
    否则只要求文件存在且大于指定最小字节数。
    """
    if not path.exists():
        return False
    actual_size = path.stat().st_size
    if expected_size is not None:
        return actual_size == expected_size
    return actual_size > min_size
