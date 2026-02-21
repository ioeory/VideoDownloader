#!/usr/bin/env python3
"""
VideoDownloader — 通用视频下载器
======================================
支持平台：
  - 通用 (YouTube / Bilibili / Vimeo / 任意 yt-dlp 支持网站)
  - DeepLearning.AI (learn.deeplearning.ai)
  - Coursera (coursera.org)

使用示例：
  # 通用下载（公开视频）
  python main.py download "https://www.youtube.com/watch?v=xxx"

  # DeepLearning.AI 课程
  python main.py deeplearning --course ai-for-everyone --cookies-file cookies.txt

  # Coursera
  python main.py coursera --url "https://www.coursera.org/..." --cookies-file cookies.txt
"""

import argparse
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from core.cookies import CookieManager
from core.downloader import DownloadTask
from core.utils import is_wsl, setup_logging
from plugins.coursera import CourseraPlugin
from plugins.deeplearning_ai import DeepLearningPlugin
from plugins.generic_ytdlp import GenericYtdlpPlugin
from plugins.kodekloud import KodeKloudPlugin

log = logging.getLogger("videodownloader")

# ─────────────────────────────────────────────
# 依赖检查
# ─────────────────────────────────────────────

def check_dependencies() -> None:
    missing = []
    for pkg in ["requests", "yt_dlp", "tqdm"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg.replace("_", "-"))
    if missing:
        print(f"❌ 缺少依赖，请运行: pip install {' '.join(missing)}")
        sys.exit(1)


# ─────────────────────────────────────────────
# 执行下载任务列表（串行 / 并发）
# ─────────────────────────────────────────────

def run_tasks(tasks: list[DownloadTask], concurrent: int = 1, delay: float = 1.0) -> None:
    """执行所有下载任务，输出汇总报告"""
    results: dict[str, list] = {"success": [], "failed": []}

    if concurrent <= 1:
        for task in tasks:
            name, ok = task.run()
            results["success" if ok else "failed"].append(name)
            time.sleep(delay)
    else:
        with ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = {executor.submit(task.run): task for task in tasks}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    name, ok = future.result()
                    results["success" if ok else "failed"].append(name)
                    log.info(f"{'✅' if ok else '❌'} {name}")
                except Exception as exc:
                    results["failed"].append(task.filename)
                    log.error(f"❌ 异常 ({task.filename}): {exc}")

    # 汇总报告
    sep = "=" * 60
    print(f"\n{sep}")
    print("📊 下载完成报告")
    print(f"   ✅ 成功: {len(results['success'])} 个")
    print(f"   ❌ 失败: {len(results['failed'])} 个")
    if results["failed"]:
        print("\n失败列表:")
        for name in results["failed"]:
            print(f"   - {name}")
    print(sep)


# ─────────────────────────────────────────────
# Cookie 参数（公共）
# ─────────────────────────────────────────────

def _add_cookie_args(parser: argparse.ArgumentParser) -> None:
    """向子命令 parser 添加公共 Cookie 参数"""
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--cookies-file", metavar="FILE",
        help="Netscape 格式 cookies.txt 文件路径（WSL 推荐）",
    )
    group.add_argument(
        "--cookie", metavar="COOKIE_STRING",
        help='手动指定 Cookie 字符串，格式: "key1=val1; key2=val2"',
    )
    parser.add_argument(
        "-b", "--browser", default="chrome",
        choices=CookieManager.SUPPORTED_BROWSERS,
        help="从哪个浏览器提取 Cookie (默认: chrome)",
    )


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """公共输出和并发参数"""
    parser.add_argument(
        "-o", "--output-dir", default="./downloads",
        help="视频保存目录 (默认: ./downloads)",
    )
    parser.add_argument(
        "-c", "--concurrent", type=int, default=1, metavar="N",
        help="并发下载数 (默认: 1，建议不超过 3)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="输出调试日志",
    )


# ─────────────────────────────────────────────
# 子命令处理器
# ─────────────────────────────────────────────

def cmd_download(args: argparse.Namespace) -> None:
    """通用下载子命令"""
    plugin = GenericYtdlpPlugin()
    cookies: dict = {}
    if args.cookies_file or args.cookie or args.browser:
        manager = CookieManager(
            cookies_file=args.cookies_file,
            cookie_str=args.cookie,
            browser=args.browser,
        )
        try:
            cookies = manager.get()
        except SystemExit:
            cookies = {}

    output_dir = Path(args.output_dir)
    tasks = plugin.get_download_tasks(
        url_or_id=args.url,
        output_dir=output_dir,
        cookies=cookies or None,
        quality=getattr(args, "quality", "best"),
        subtitle=getattr(args, "subtitle", False),
    )
    print(f"▶ 通用下载: {args.url}")
    run_tasks(tasks, concurrent=args.concurrent)


def cmd_deeplearning(args: argparse.Namespace) -> None:
    """DeepLearning.AI 子命令"""
    plugin = DeepLearningPlugin()
    manager = CookieManager(
        cookies_file=args.cookies_file,
        cookie_str=args.cookie,
        browser=args.browser,
        domain_filter="deeplearning.ai",
    )
    cookies = manager.get()

    output_dir = Path(args.output_dir)
    url_or_id = args.course or args.url or ""
    if not url_or_id:
        print("❌ 请通过 --course 或 --url 指定课程")
        sys.exit(1)

    weeks: Optional[list[int]] = args.weeks if args.weeks else None
    tasks = plugin.get_download_tasks(
        url_or_id=url_or_id,
        output_dir=output_dir,
        cookies=cookies,
        weeks=weeks,
    )

    wsl_tag = " [WSL]" if is_wsl() else ""
    print(f"▶ DeepLearning.AI 课程: {url_or_id}{wsl_tag}")
    print(f"  Week: {weeks or '全部'} | 共 {len(tasks)} 个 Lesson")
    run_tasks(tasks, concurrent=args.concurrent)


def cmd_coursera(args: argparse.Namespace) -> None:
    """Coursera 子命令"""
    plugin = CourseraPlugin()
    manager = CookieManager(
        cookies_file=args.cookies_file,
        cookie_str=args.cookie,
        browser=args.browser,
        domain_filter="coursera.org",
    )
    cookies = manager.get()

    output_dir = Path(args.output_dir)
    tasks = plugin.get_download_tasks(
        url_or_id=args.url,
        output_dir=output_dir,
        cookies=cookies,
        quality=getattr(args, "quality", "best"),
        subtitle=getattr(args, "subtitle", True),
    )
    print(f"▶ Coursera: {args.url}")
    run_tasks(tasks, concurrent=args.concurrent)


def cmd_kodekloud(args: argparse.Namespace) -> None:
    """KodeKloud 子命令"""
    plugin = KodeKloudPlugin()
    manager = CookieManager(
        cookies_file=args.cookies_file,
        cookie_str=args.cookie,
        browser=args.browser,
        domain_filter="learn.kodekloud.com",
    )
    cookies = manager.get()

    output_dir = Path(args.output_dir)
    tasks = plugin.get_download_tasks(
        url_or_id=args.url,
        output_dir=output_dir,
        cookies=cookies,
        quality=getattr(args, "quality", "720p"),
    )
    print(f"▶ KodeKloud: {args.url}")
    run_tasks(tasks, concurrent=args.concurrent)


def cmd_list_courses(_args: argparse.Namespace) -> None:
    """列出内置支持的 DeepLearning.AI 课程"""
    plugin = DeepLearningPlugin()
    courses = plugin.list_builtin_courses()
    print("📚 内置支持的 DeepLearning.AI 课程:")
    for slug in courses:
        print(f"   - {slug}")


# ─────────────────────────────────────────────
# 主 CLI
# ─────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vd",
        description="VideoDownloader — 通用视频下载器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py download "https://www.youtube.com/watch?v=jNQXAC9IVRw"
  python main.py deeplearning --course ai-for-everyone --cookies-file cookies.txt
  python main.py deeplearning --course ai-for-everyone --weeks 1 2 -c 2
  python main.py coursera --url "https://www.coursera.org/learn/..." --cookies-file cookies.txt
  python main.py list-courses
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── download ──
    p_dl = subparsers.add_parser("download", help="通用下载（YouTube/Bilibili/Vimeo 等）")
    p_dl.add_argument("url", help="视频 URL")
    p_dl.add_argument(
        "-q", "--quality", default="best",
        choices=["best", "1080p", "720p", "480p", "audio"],
        help="画质选择 (默认: best)",
    )
    p_dl.add_argument("--subtitle", action="store_true", help="下载字幕")
    _add_cookie_args(p_dl)
    _add_common_args(p_dl)
    p_dl.set_defaults(func=cmd_download)

    # ── deeplearning ──
    p_dai = subparsers.add_parser("deeplearning", aliases=["dai"], help="DeepLearning.AI 课程下载")
    group = p_dai.add_mutually_exclusive_group()
    group.add_argument("--course", metavar="SLUG", help="课程 slug（如 ai-for-everyone）")
    group.add_argument("--url", metavar="URL", help="课程页面 URL")
    p_dai.add_argument(
        "--weeks", type=int, nargs="+", metavar="N",
        help="指定 Week（如 --weeks 1 2），默认下载全部",
    )
    _add_cookie_args(p_dai)
    _add_common_args(p_dai)
    p_dai.set_defaults(func=cmd_deeplearning)

    # ── coursera ──
    p_crs = subparsers.add_parser("coursera", help="Coursera 课程下载")
    p_crs.add_argument("--url", required=True, metavar="URL", help="Coursera 课程/视频 URL")
    p_crs.add_argument(
        "-q", "--quality", default="best",
        choices=["best", "720p", "360p"],
        help="画质选择 (默认: best)",
    )
    p_crs.add_argument("--no-subtitle", action="store_true", help="不下载字幕")
    _add_cookie_args(p_crs)
    _add_common_args(p_crs)
    p_crs.set_defaults(func=cmd_coursera)

    # ── kodekloud ──
    p_kk = subparsers.add_parser("kodekloud", help="KodeKloud 课程下载")
    p_kk.add_argument("--url", required=True, metavar="URL", help="KodeKloud 课程 URL")
    p_kk.add_argument(
        "-q", "--quality", default="720p",
        choices=["1080p", "720p", "480p", "360p"],
        help="画质选择 (默认: 720p)",
    )
    _add_cookie_args(p_kk)
    _add_common_args(p_kk)
    p_kk.set_defaults(func=cmd_kodekloud)

    # ── list-courses ──
    p_list = subparsers.add_parser("list-courses", help="列出内置支持的 DeepLearning.AI 课程")
    p_list.set_defaults(func=cmd_list_courses)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # 日志初始化
    verbose = getattr(args, "verbose", False)
    setup_logging(verbose=verbose)

    # 依赖检查
    check_dependencies()

    # 执行子命令
    args.func(args)


if __name__ == "__main__":
    main()
