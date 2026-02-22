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

from videodownloader.core.cookies import CookieManager
from videodownloader.core.downloader import DownloadTask
from videodownloader.core.utils import is_wsl, setup_logging
from videodownloader.plugins.coursera import CourseraPlugin
from videodownloader.plugins.deeplearning_ai import DeepLearningPlugin
from videodownloader.plugins.generic_ytdlp import GenericYtdlpPlugin
from videodownloader.plugins.kodekloud import KodeKloudPlugin
from videodownloader.plugins.skills_google import SkillsGooglePlugin
from videodownloader.plugins.harvard import HarvardPlugin

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

def _inject_ytdlp_cookies(tasks: list[DownloadTask], args: argparse.Namespace) -> None:
    """向任务注入通用的 yt-dlp cookie 和防机器人参数"""
    for t in tasks:
        if getattr(t, "ignore_global_cookies", False):
            continue
        if t.extra_opts is None:
            t.extra_opts = {}
        
        # 优先使用原始 cookies_file 直接传给 yt-dlp，避免 downloader.py 重写丢失域名
        if getattr(args, "cookies_file", None):
            t.extra_opts["cookiefile"] = args.cookies_file
        # 否则如果是直接读取浏览器
        elif not getattr(args, "cookie", None) and getattr(args, "browser", None) and not is_wsl():
            t.extra_opts["cookiesfrombrowser"] = (args.browser, )

        # 增加 YouTube 防机器人的 extractor args
        if "extractor_args" not in t.extra_opts:
            t.extra_opts["extractor_args"] = {}
        if "youtube" not in t.extra_opts["extractor_args"]:
            t.extra_opts["extractor_args"]["youtube"] = {}


def run_tasks(tasks: list[DownloadTask], concurrent: int = 1, delay: float = 1.0) -> None:
    """执行所有下载任务，输出汇总报告"""
    results: dict[str, list] = {"success": [], "partial": [], "failed": []}
    total = len(tasks)
    
    if total == 0:
        log.warning("没有需要下载的任务。")
        return

    log.info(f"发现 {total} 个下载子任务，准备执行...")

    if concurrent <= 1:
        for i, task in enumerate(tasks, 1):
            log.info(f"\n---> 开始执行任务 [{i}/{total}]: {task.filename}")
            name, status = task.run()
            if status == "success":
                results["success"].append(name)
            elif status == "partial":
                results["partial"].append(name)
            else:
                results["failed"].append(name)
            time.sleep(delay)
    else:
        with ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = {executor.submit(task.run): (i, task) for i, task in enumerate(tasks, 1)}
            for future in as_completed(futures):
                i, task = futures[future]
                try:
                    name, status = future.result()
                    if status == "success":
                        results["success"].append(name)
                        log.info(f"[{i}/{total}] ✅ {name}")
                    elif status == "partial":
                        results["partial"].append(name)
                        log.info(f"[{i}/{total}] ⚠️ 部分/瑕疵: {name}")
                    else:
                        results["failed"].append(name)
                        log.info(f"[{i}/{total}] ❌ {name}")
                except Exception as exc:
                    results["failed"].append(task.filename)
                    log.error(f"[{i}/{total}] ❌ 异常 ({task.filename}): {exc}")

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
        help="输出调试日志 (相当于 --log-level DEBUG)",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="设置日志输出级别 (默认: INFO)",
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
        playlist_items=getattr(args, "playlist_items", None),
    )
    print(f"▶ 通用下载: {args.url}")
    _inject_ytdlp_cookies(tasks, args)
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
    _inject_ytdlp_cookies(tasks, args)
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
    _inject_ytdlp_cookies(tasks, args)
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
    _inject_ytdlp_cookies(tasks, args)
    run_tasks(tasks, concurrent=args.concurrent)


def cmd_skillsgoogle(args: argparse.Namespace) -> None:
    """Skills Google 子命令"""
    plugin = SkillsGooglePlugin()
    manager = CookieManager(
        cookies_file=args.cookies_file,
        cookie_str=args.cookie,
        browser=args.browser,
        domain_filter="skills.google",
    )
    cookies = manager.get()

    output_dir = Path(args.output_dir)
    tasks = plugin.get_download_tasks(
        url_or_id=args.url,
        output_dir=output_dir,
        cookies=cookies,
        quality=getattr(args, "quality", "1080p"),
    )
    print(f"▶ Skills Google: {args.url}")
    _inject_ytdlp_cookies(tasks, args)
    run_tasks(tasks, concurrent=args.concurrent)


def cmd_harvard(args: argparse.Namespace) -> None:
    """Harvard 子命令"""
    plugin = HarvardPlugin()
    cookies: dict = {}
    
    # 因为 harvard.edu 通常不需要鉴权，所以尝试获取 cookie 即可，失败了不阻断下载
    if getattr(args, "cookies_file", None) or getattr(args, "cookie", None) or getattr(args, "browser", None):
        manager = CookieManager(
            cookies_file=args.cookies_file,
            cookie_str=args.cookie,
            browser=args.browser,
            domain_filter="harvard.edu",
        )
        try:
            cookies = manager.get()
        except SystemExit:
            cookies = {}
        except Exception:
            cookies = {}

    output_dir = Path(args.output_dir)
    tasks = plugin.get_download_tasks(
        url_or_id=args.url,
        output_dir=output_dir,
        cookies=cookies,
        quality=getattr(args, "quality", "best"),
    )
    print(f"▶ Harvard: {args.url}")
    _inject_ytdlp_cookies(tasks, args)
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
  vd download "https://www.youtube.com/watch?v=jNQXAC9IVRw"
  vd deeplearning --course ai-for-everyone --cookies-file cookies.txt
  vd deeplearning --course ai-for-everyone --weeks 1 2 -c 2
  vd coursera --url "https://www.coursera.org/learn/..." --cookies-file cookies.txt
  vd skillsgoogle --url "https://www.skills.google/paths/1951/..." --cookies-file cookies.txt
  vd harvard --url "https://cs50.harvard.edu/python/" --quality 1080p
  vd list-courses
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── download ──
    p_dl = subparsers.add_parser("download", help="通用下载（YouTube/Bilibili/Vimeo 等）")
    p_dl.add_argument("url", help="视频 URL")
    p_dl.add_argument(
        "-q", "--quality", default="best",
        choices=["best", "4k", "1080p", "720p", "480p", "audio"],
        help="画质选择 (默认: best)",
    )
    p_dl.add_argument("--subtitle", action="store_true", help="下载字幕")
    p_dl.add_argument("--playlist-items", metavar="ITEM_SPEC", help="指定下载播放列表的范围 (如 1-25, 1,3,5-7)")
    _add_cookie_args(p_dl)
    _add_common_args(p_dl)
    p_dl.set_defaults(func=cmd_download, browser=None)

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

    # ── skillsgoogle ──
    p_sg = subparsers.add_parser("skillsgoogle", aliases=["skills"], help="Skills Google 课程下载")
    p_sg.add_argument("--url", required=True, metavar="URL", help="Skills Google 课程 URL")
    p_sg.add_argument(
        "-q", "--quality", default="1080p",
        choices=["1080p", "720p", "480p", "360p"],
        help="画质选择 (默认: 1080p)",
    )
    _add_cookie_args(p_sg)
    _add_common_args(p_sg)
    p_sg.set_defaults(func=cmd_skillsgoogle)

    # ── harvard ──
    p_hvd = subparsers.add_parser("harvard", help="Harvard 课程下载 (CS50等)")
    p_hvd.add_argument("--url", required=True, metavar="URL", help="Harvard 课程/页面 URL")
    p_hvd.add_argument(
        "-q", "--quality", default="best",
        choices=["best", "4k", "1080p", "720p", "480p", "360p"],
        help="画质选择 (默认: best)",
    )
    _add_cookie_args(p_hvd)
    _add_common_args(p_hvd)
    p_hvd.set_defaults(func=cmd_harvard)

    # ── list-courses ──
    p_list = subparsers.add_parser("list-courses", help="列出内置支持的 DeepLearning.AI 课程")
    p_list.set_defaults(func=cmd_list_courses)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # 日志初始化
    verbose = getattr(args, "verbose", False)
    log_level_str = getattr(args, "log_level", "INFO")
    
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }
    log_level = level_map.get(log_level_str, logging.INFO)
    
    setup_logging(verbose=verbose, log_level=log_level)

    # 依赖检查
    check_dependencies()

    # 执行子命令
    args.func(args)


if __name__ == "__main__":
    main()
