#!/usr/bin/env python3
"""
VideoDownloader CLI Entrypoint
"""

import sys
from pathlib import Path

# 取工程根目录加入系统路径以确保引用有效
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from videodownloader.main import main

if __name__ == "__main__":
    main()
