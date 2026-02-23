#!/usr/bin/env python3
"""
插件基类定义
所有平台插件必须继承 BasePlugin 并实现其抽象方法。
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from videodownloader.core.downloader import DownloadTask


class BasePlugin(ABC):
    """
    视频下载插件基类

    子类需定义：
      name        - 插件名称（唯一标识）
      description - 功能描述
      domains     - 匹配的域名列表（用于 URL 自动分派）
    """

    name: str = "base"
    description: str = "基础插件"
    domains: list[str] = []

    @abstractmethod
    def get_download_tasks(
        self,
        url_or_id: str,
        output_dir: Path,
        cookies: Optional[dict] = None,
        **kwargs,
    ) -> list[DownloadTask]:
        """
        根据输入 URL 或 ID，返回待下载的任务列表。

        Args:
            url_or_id:  URL 或平台特定的资源 ID（课程 slug 等）
            output_dir: 输出根目录
            cookies:    Cookie 字典（可选）
            **kwargs:   平台特定参数

        Returns:
            DownloadTask 列表
        """
        ...

    def get_cookies_domain(self) -> str:
        """返回该插件的 Cookie 所属域名（用于写 Netscape 文件）"""
        return self.domains[0] if self.domains else ".example.com"

    def can_handle(self, url: str) -> bool:
        """判断本插件是否能处理该 URL"""
        return any(domain in url for domain in self.domains)

    def _t(self, key: str, default: str, *args, **kwargs) -> str:
        """翻译助手"""
        t = kwargs.get("translator")
        if t: return t(key).format(*args)
        return default.format(*args)

    def __repr__(self) -> str:
        return f"<Plugin: {self.name}>"
