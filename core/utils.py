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


# 检测 ffmpeg 是否存在
HAS_FFMPEG = shutil.which("ffmpeg") is not None


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


def file_is_complete(path: Path, min_size: int = 1024) -> bool:
    """判断文件是否已完整下载（存在且大于最小字节数）"""
    return path.exists() and path.stat().st_size > min_size
