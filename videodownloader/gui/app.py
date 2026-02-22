import customtkinter as ctk
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import filedialog, messagebox
import threading
import logging
import sys
from pathlib import Path

# Videodownloader imports
from videodownloader.core.cookies import CookieManager
from videodownloader.core.downloader import DownloadTask
from videodownloader.core.utils import setup_logging
from videodownloader.plugins.generic_ytdlp import GenericYtdlpPlugin
from videodownloader.plugins.harvard import HarvardPlugin
from videodownloader.plugins.deeplearning_ai import DeepLearningPlugin
from videodownloader.plugins.coursera import CourseraPlugin
from videodownloader.plugins.kodekloud import KodeKloudPlugin
from videodownloader.plugins.skills_google import SkillsGooglePlugin

log = logging.getLogger("videodownloader")

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        # Configure color tags for logging levels
        self.text_widget.tag_config("ERROR", foreground="#FF4C4C")   # Red
        self.text_widget.tag_config("WARNING", foreground="#FFB74D") # Orange
        self.text_widget.tag_config("INFO", foreground="#E0E0E0")    # White/Gray
        self.text_widget.tag_config("DEBUG", foreground="#90A4AE")   # Blueish Gray

    def emit(self, record):
        msg = self.format(record)
        level = record.levelname
        
        def append():
            self.text_widget.configure(state="normal")
            if level in ["ERROR", "WARNING", "INFO", "DEBUG"]:
                self.text_widget.insert("end", msg + "\n", level)
            else:
                self.text_widget.insert("end", msg + "\n")
            self.text_widget.see("end")
            self.text_widget.configure(state="disabled")
            
        try:
            self.text_widget.after(0, append)
        except Exception:
            pass

def enable_undo(entry, string_var=None):
    if not isinstance(entry, ctk.CTkEntry):
        return
    if not string_var:
        string_var = ctk.StringVar()
        entry.configure(textvariable=string_var)
        
    stack = [""]
    ptr = [0]
    
    def on_change(*args):
        val = string_var.get()
        if getattr(entry, '_is_undoing', False):
            return
        if not stack or stack[ptr[0]] != val:
            del stack[ptr[0]+1:]
            stack.append(val)
            ptr[0] += 1
            if len(stack) > 50:
                stack.pop(0)
                ptr[0] -= 1

    def on_undo(event):
        if ptr[0] > 0:
            entry._is_undoing = True
            ptr[0] -= 1
            val = stack[ptr[0]]
            string_var.set(val)
            entry._is_undoing = False
        return "break"

    def on_redo(event):
        if ptr[0] < len(stack) - 1:
            entry._is_undoing = True
            ptr[0] += 1
            val = stack[ptr[0]]
            string_var.set(val)
            entry._is_undoing = False
        return "break"

    string_var.trace_add("write", on_change)
    entry.bind("<Control-z>", on_undo, add="+")
    entry.bind("<Control-Z>", on_undo, add="+")
    entry.bind("<Control-y>", on_redo, add="+")
    entry.bind("<Control-Y>", on_redo, add="+")

class VideoDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # State vars
        self.is_paused = False
        self.is_stopped = False
        self.pause_event = threading.Event()
        self.pause_event.set() # Set initial state to not paused
        self.current_lang = "en"
        self.i18n = {
            "en": {
                "title": "VideoDownloader - Universal Video Downloader",
                "url": "Video/Course URL:",
                "platform": "Platform:",
                "quality": "Max Quality:",
                "outdir": "Output Dir:",
                "browse": "Browse...",
                "cookies": "Cookies:",
                "loglevel": "Log Level:",
                "threads": "Concurrency (Threads):",
                "waiting": "Waiting...",
                "start": "Start Download",
                "pause": "Pause",
                "resume": "Resume",
                "stop": "Stop",
                "playlist_range": "Playlist Items:",
                "playlist_ph": "e.g. 1-25 or 1,3,5 (blank for all)",
                "subtitles": "Download Subtitles",
                "harvard_info": "Info: Harvard mode auto-detects playlists and downloads videos, PDFs, and assets.",
                "weeks": "Specific Week(s):",
                "weeks_ph": "e.g. 1 2 (space separated, blank for all)",
                "welcome": "Welcome to VideoDownloader GUI! Stuttering during startup is normal.",
                "lang_toggle": "Language: ZH",
                "cookie_none": "None (No login)",
                "cookie_chrome": "Chrome Browser",
                "cookie_edge": "Edge Browser",
                "cookie_firefox": "Firefox Browser",
                "cookie_brave": "Brave Browser",
                "cookie_clipboard": "Clipboard (Paste text)",
                "cookie_file": "Select cookies.txt...",
                "warning": "Warning",
                "enter_url": "Please enter URL or Course Slug",
                "paused_stat": "Paused: ",
                "downloading": "Downloading: ",
                "speed": "   |   Speed: ",
                "concurrent_dl": "Concurrent downloading... Check logs",
                "processing": ", processing...",
                "finished": "Finished: ",
                "preparing": "Preparing...",
                "stopping": "Force stopping, please wait...",
                "confirm_title": "Confirmation",
                "confirm_stop": "Stop current download and cancel queued tasks?",
                "log_start": "🚀 Starting download task: ",
                "log_cookie_try": "Trying to get Cookie from ",
                "log_cookie_succ": "Successfully extracted ",
                "log_cookie_succ2": " Cookie items.",
                "log_cookie_fail": "Failed to get Cookie: ",
                "log_no_task": "No download tasks could be parsed.",
                "log_found_tasks": "Found ",
                "log_found_tasks2": " sub-tasks, preparing download...",
                "log_start_sub": "Starting task ",
                "log_terminated": "Task terminated: ",
                "log_abort": "Queue execution aborted",
                "log_success": "✅ Queue executed! Tasks Success: {}, Failed: {}. Processed {} media files/segments.",
                "log_partial": "Partial: ",
                "log_failed": "Failed: "
            },
            "zh": {
                "title": "VideoDownloader - 通用视频下载器",
                "url": "视频/课程 URL:",
                "platform": "下载平台:",
                "quality": "最高画质:",
                "outdir": "输出目录:",
                "browse": "浏览...",
                "cookies": "Cookies 来源:",
                "loglevel": "日志级别:",
                "threads": "并发线程:",
                "waiting": "等待下载...",
                "start": "开始下载",
                "pause": "暂停",
                "resume": "继续",
                "stop": "停止",
                "playlist_range": "播放列表范围:",
                "playlist_ph": "如 1-25 或 1,3,5 (留空: 全部)",
                "subtitles": "下载字幕",
                "harvard_info": "说明: Harvard 模式支持自动探测播放列表。全自动提取 YouTube、直链、PDF。",
                "weeks": "指定 Week(s):",
                "weeks_ph": "如 1 2 (空格分隔, 留空: 全部)",
                "welcome": "欢迎使用 VideoDownloader GUI！启动期如果有卡顿属于正常现象。",
                "lang_toggle": "Language: EN",
                "cookie_none": "无 (免登录)",
                "cookie_chrome": "Chrome 浏览器",
                "cookie_edge": "Edge 浏览器",
                "cookie_firefox": "Firefox 浏览器",
                "cookie_brave": "Brave 浏览器",
                "cookie_clipboard": "剪贴板 (粘贴文本)",
                "cookie_file": "选择 cookies.txt...",
                "warning": "警告",
                "enter_url": "请输入 URL 或 Course Slug",
                "paused_stat": "已暂停: ",
                "downloading": "正在下载: ",
                "speed": "   |   速度: ",
                "concurrent_dl": "并发下载中 (多线程活动)... 请查看上方日志",
                "processing": "，正在合并处理...",
                "finished": "已下载完成: ",
                "preparing": "准备下载...",
                "stopping": "正在强制停止，请稍候...",
                "confirm_title": "确认",
                "confirm_stop": "确定要停止当前下载(会取消后续任务)吗？",
                "log_start": "🚀 开始下载任务: ",
                "log_cookie_try": "正在尝试获取 Cookie ",
                "log_cookie_succ": "成功获取到 ",
                "log_cookie_succ2": " 条记录。",
                "log_cookie_fail": "获取 Cookie 失败: ",
                "log_no_task": "没有解析出任何下载任务。",
                "log_found_tasks": "发现 ",
                "log_found_tasks2": " 个子任务，准备下载...",
                "log_start_sub": "开始执行任务 ",
                "log_terminated": "任务已终止: ",
                "log_abort": "队列执行已中止",
                "log_success": "✅ 队列执行完毕！成功任务 {}，失败 {}。本次共已下载或合并 {} 个媒体分段/文件。",
                "log_partial": "瑕疵 ",
                "log_failed": "失败 "
            }
        }

        self.title("VideoDownloader - Universal Video Downloader")
        self.geometry("820x720")
        
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        
        # 1. URL 输入区
        self.frame_url = ctk.CTkFrame(self)
        self.frame_url.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.frame_url.grid_columnconfigure(1, weight=1)
        
        self.lbl_url = ctk.CTkLabel(self.frame_url, text=self.t("url"))
        self.lbl_url.grid(row=0, column=0, padx=10, pady=10)
        
        self.entry_url = ctk.CTkEntry(self.frame_url, placeholder_text="https://...")
        self.entry_url.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        enable_undo(self.entry_url)
        self.btn_lang = ctk.CTkButton(self.frame_url, text=self.t("lang_toggle"), width=120, command=self.toggle_language, fg_color="#455A64", hover_color="#37474F")
        self.btn_lang.grid(row=0, column=2, padx=10, pady=10)

        # 2. 核心配置区 (平台 & 动态配置 & 环境)
        self.frame_config = ctk.CTkFrame(self)
        self.frame_config.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.frame_config.grid_columnconfigure(1, weight=1)
        
        # Platform Selection
        self.lbl_platform = ctk.CTkLabel(self.frame_config, text=self.t("platform"))
        self.lbl_platform.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.platform_var = ctk.StringVar(value="Generic (YouTube/Bilibili etc.)")
        self.combo_platform = ctk.CTkComboBox(self.frame_config, variable=self.platform_var, state="readonly",
            values=["Generic (YouTube/Bilibili etc.)", "Harvard (CS50)", "DeepLearning.AI", "Coursera", "KodeKloud", "Skills Google"],
            command=self.on_platform_change)
        self.combo_platform.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Quality Selection
        self.lbl_quality = ctk.CTkLabel(self.frame_config, text=self.t("quality"))
        self.lbl_quality.grid(row=0, column=2, padx=10, pady=10, sticky="w")
        
        self.quality_var = ctk.StringVar(value="best")
        self.combo_quality = ctk.CTkComboBox(self.frame_config, variable=self.quality_var, state="readonly",
            values=["best", "4k", "1080p", "720p", "480p", "audio"])
        self.combo_quality.grid(row=0, column=3, padx=10, pady=10, sticky="ew")
        
        # Dynamic Options Frame
        self.frame_dynamic = ctk.CTkFrame(self.frame_config, fg_color="transparent")
        self.frame_dynamic.grid(row=1, column=0, columnspan=4, padx=0, pady=0, sticky="ew")
        self.frame_dynamic.grid_columnconfigure(1, weight=1)
        
        # Dynamic vars
        self.playlist_items_var = ctk.StringVar()
        self.subtitle_var = ctk.BooleanVar(value=True)
        self.weeks_var = ctk.StringVar()
        
        self.build_dynamic_options()
        
        # Environment (Output Dir & Cookies)
        self.lbl_outdir = ctk.CTkLabel(self.frame_config, text=self.t("outdir"))
        self.lbl_outdir.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        
        self.outdir_var = ctk.StringVar(value=str(Path("./downloads").absolute()))
        self.entry_outdir = ctk.CTkEntry(self.frame_config, textvariable=self.outdir_var)
        self.entry_outdir.grid(row=2, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        enable_undo(self.entry_outdir, self.outdir_var)
        
        self.btn_browse = ctk.CTkButton(self.frame_config, text=self.t("browse"), command=self.browse_dir, width=60)
        self.btn_browse.grid(row=2, column=3, padx=10, pady=10)
        
        self.lbl_cookie = ctk.CTkLabel(self.frame_config, text=self.t("cookies"))
        self.lbl_cookie.grid(row=3, column=0, padx=10, pady=10, sticky="w")
        
        self.cookie_src_var = ctk.StringVar(value="None (No login)")
        self.combo_cookie_src = ctk.CTkComboBox(self.frame_config, variable=self.cookie_src_var, state="readonly",
            values=[self.t('cookie_none'), self.t('cookie_chrome'), self.t('cookie_edge'), self.t('cookie_firefox'), self.t('cookie_brave'), self.t('cookie_clipboard'), self.t('cookie_file')],
            command=self.on_cookie_src_change)
        self.combo_cookie_src.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        
        self.cookie_val_var = ctk.StringVar()
        self.entry_cookie_val = ctk.CTkEntry(self.frame_config, textvariable=self.cookie_val_var, state="disabled")
        self.entry_cookie_val.grid(row=3, column=2, columnspan=2, padx=10, pady=10, sticky="ew")
        enable_undo(self.entry_cookie_val, self.cookie_val_var)

        # Log Level
        self.lbl_loglevel = ctk.CTkLabel(self.frame_config, text=self.t("loglevel"))
        self.lbl_loglevel.grid(row=4, column=0, padx=10, pady=10, sticky="w")
        
        self.loglevel_var = ctk.StringVar(value="INFO")
        self.combo_loglevel = ctk.CTkComboBox(self.frame_config, variable=self.loglevel_var, state="readonly",
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            command=self.on_loglevel_change)
        self.combo_loglevel.grid(row=4, column=1, padx=10, pady=10, sticky="ew")

        # Thread count
        self.lbl_threads = ctk.CTkLabel(self.frame_config, text=self.t("threads"))
        self.lbl_threads.grid(row=4, column=2, padx=10, pady=10, sticky="w")
        
        self.threads_var = ctk.StringVar(value="1")
        self.combo_threads = ctk.CTkComboBox(self.frame_config, variable=self.threads_var, state="readonly",
            values=["1", "2", "3", "4", "5"])
        self.combo_threads.grid(row=4, column=3, padx=10, pady=10, sticky="ew")

        # 3. 进度与日志区
        self.frame_log = ctk.CTkFrame(self)
        self.frame_log.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.frame_log.grid_columnconfigure(0, weight=1)
        self.frame_log.grid_rowconfigure(0, weight=1)
        
        self.textbox_log = ctk.CTkTextbox(self.frame_log, state="disabled", wrap="word", font=("Consolas", 12))
        self.textbox_log.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        self.lbl_status = ctk.CTkLabel(self.frame_log, text=self.t("waiting"), font=("", 13), text_color="gray", anchor="w")
        self.lbl_status.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        
        self.progress_var = ctk.DoubleVar(value=0)
        self.progressbar = ctk.CTkProgressBar(self.frame_log, variable=self.progress_var)
        self.progressbar.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.progressbar.set(0) # initialize to 0
        
        # 4. 操作区
        self.frame_actions = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_actions.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.frame_actions.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.btn_download = ctk.CTkButton(self.frame_actions, text=self.t("start"), height=45, font=("", 16, "bold"), command=self.start_download)
        self.btn_download.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        self.btn_pause = ctk.CTkButton(self.frame_actions, text=self.t("pause"), height=45, font=("", 16, "bold"), command=self.toggle_pause, state="disabled")
        self.btn_pause.grid(row=0, column=1, padx=10, sticky="ew")
        
        self.btn_stop = ctk.CTkButton(self.frame_actions, text=self.t("stop"), height=45, font=("", 16, "bold"), command=self.stop_download, state="disabled", fg_color="#C62828", hover_color="#b71c1c")
        self.btn_stop.grid(row=0, column=2, padx=(10, 0), sticky="ew")
        
        # Save default colors for resetting later
        self.default_btn_color = self.btn_download.cget("fg_color")
        self.default_btn_hover = self.btn_download.cget("hover_color")
        
        # Setup logging
        setup_logging(verbose=True)
        handler = TextHandler(self.textbox_log)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
        # attach handler to root logger
        logging.getLogger().addHandler(handler)
        
        # yt-dlp logger adapter
        class YtdlpLogger:
            def debug(self, msg):
                # For compatibility with youtube-dl, both debug and info are passed into debug
                if msg.startswith('[debug] '):
                    if logging.getLogger().level <= logging.DEBUG:
                        log.debug(msg)
                else:
                    self.info(msg)
                    
            def info(self, msg):
                # ignore noise unless in DEBUG mode
                if logging.getLogger().level > logging.DEBUG:
                    if "frag" in msg.lower() or "eta" in msg.lower() or "downloading webpage" in msg.lower():
                        return
                    if "[download]" in msg and "Destination:" not in msg and "Finished" not in msg:
                        return
                log.info(msg)
                
            def warning(self, msg):
                log.warning(msg)
                # 针对 Node.js 缺失检测的强提醒
                if "JavaScript runtime" in msg or "challenge solver" in msg:
                    log.error("➡️ **CRITICAL TIP**: Please install Node.js (https://nodejs.org/) to solve YouTube anti-bot challenges! Without it, HD videos cannot be decrypted. Please restart this GUI after installation.")
            def error(self, msg):
                log.error(msg)
                if "Requested format is not available" in msg:
                    log.error("➡️ **CRITICAL TIP**: Format unavailable is likely caused by missing Node.js! Install Node.js from https://nodejs.org/")
        self.ytdlp_logger = YtdlpLogger()

        self.on_loglevel_change(self.loglevel_var.get())
        
        self.update_ui_texts()
        self.on_platform_change(self.platform_var.get())
        
        log.info(self.t("welcome"))


    def t(self, key):
        if not hasattr(self, 'i18n') or not hasattr(self, 'current_lang'): return key
        return self.i18n.get(self.current_lang, {}).get(key, key)

    def toggle_language(self):
        self.current_lang = "zh" if self.current_lang == "en" else "en"
        self.update_ui_texts()
        self.build_dynamic_options()
        
    def update_ui_texts(self):
        self.title(self.t("title"))
        self.lbl_url.configure(text=self.t("url"))
        self.lbl_platform.configure(text=self.t("platform"))
        self.lbl_quality.configure(text=self.t("quality"))
        self.lbl_outdir.configure(text=self.t("outdir"))
        self.btn_browse.configure(text=self.t("browse"))
        self.lbl_cookie.configure(text=self.t("cookies"))
        self.lbl_loglevel.configure(text=self.t("loglevel"))
        self.lbl_threads.configure(text=self.t("threads"))
        
        btn_states = [self.t('start'), self.t('pause'), self.t('resume'), self.t('stop')]
        if self.btn_download.cget("text") in ["Start Download", "开始下载"] or self.btn_download.cget("text") in btn_states:
            self.btn_download.configure(text=self.t("start"))
        if self.btn_pause.cget("text") in ["Pause", "暂停", "⏸ Pause"]:
            self.btn_pause.configure(text=self.t("pause"))
        elif self.btn_pause.cget("text") in ["Resume", "继续", "▶ Resume"]:
            self.btn_pause.configure(text=self.t("resume"))
        if self.btn_stop.cget("text") in ["Stop", "停止", "⏹ Stop"]:
            self.btn_stop.configure(text=self.t("stop"))
            
        if hasattr(self, 'btn_lang'):
            self.btn_lang.configure(text=self.t("lang_toggle"))
        
        if self.lbl_status.cget("text") in ["Waiting...", "等待下载..."]:
            self.lbl_status.configure(text=self.t("waiting"))
            
        # Update combo cookie values
        cv = [self.t('cookie_none'), self.t('cookie_chrome'), self.t('cookie_edge'), self.t('cookie_firefox'), self.t('cookie_brave'), self.t('cookie_clipboard'), self.t('cookie_file')]
        self.combo_cookie_src.configure(values=cv)

    def build_dynamic_options(self):
        # Clear dynamic frame
        for widget in self.frame_dynamic.winfo_children():
            widget.destroy()
            
        platform = self.platform_var.get()
        
        if platform == "Generic (YouTube/Bilibili etc.)":
            self.lbl_quality.grid()
            self.combo_quality.grid()
            
            lbl1 = ctk.CTkLabel(self.frame_dynamic, text=self.t("playlist_range"))
            lbl1.grid(row=0, column=0, padx=10, pady=5, sticky="w")
            ent1 = ctk.CTkEntry(self.frame_dynamic, textvariable=self.playlist_items_var, placeholder_text=self.t("playlist_ph"))
            ent1.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
            enable_undo(ent1, self.playlist_items_var)
            
            chk1 = ctk.CTkCheckBox(self.frame_dynamic, text=self.t("subtitles"), variable=self.subtitle_var)
            chk1.grid(row=0, column=2, padx=10, pady=5, sticky="w")
            
        elif platform == "Harvard (CS50)":
            self.lbl_quality.grid()
            self.combo_quality.grid()
            
            lbl1 = ctk.CTkLabel(self.frame_dynamic, text=self.t("harvard_info"))
            lbl1.grid(row=0, column=0, columnspan=4, padx=10, pady=5, sticky="w")
            
        elif platform == "DeepLearning.AI":
            self.lbl_quality.grid_remove() # Deeplearning ai overrides quality
            self.combo_quality.grid_remove()
            
            lbl1 = ctk.CTkLabel(self.frame_dynamic, text=self.t("weeks"))
            lbl1.grid(row=0, column=0, padx=10, pady=5, sticky="w")
            ent1 = ctk.CTkEntry(self.frame_dynamic, textvariable=self.weeks_var, placeholder_text=self.t("weeks_ph"))
            ent1.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
            enable_undo(ent1, self.weeks_var)
            
        elif platform == "Coursera":
            self.lbl_quality.grid()
            self.combo_quality.grid()
            
            chk1 = ctk.CTkCheckBox(self.frame_dynamic, text=self.t("subtitles"), variable=self.subtitle_var)
            chk1.grid(row=0, column=0, padx=10, pady=5, sticky="w")
            
        else:
            self.lbl_quality.grid()
            self.combo_quality.grid()

    def on_platform_change(self, choice):
        self.build_dynamic_options()
        
    def on_loglevel_change(self, choice):
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
        }
        level = level_map.get(choice, logging.INFO)
        log.setLevel(level)
        logging.getLogger().setLevel(level)
        for handler in logging.getLogger().handlers:
            handler.setLevel(level)
        
    def on_cookie_src_change(self, choice):
        if "cookies.txt" in choice:
            file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
            if file_path:
                self.cookie_val_var.set(file_path)
                self.entry_cookie_val.configure(state="normal")
            else:
                self.cookie_src_var.set(self.t("cookie_none"))
                self.cookie_val_var.set("")
                self.entry_cookie_val.configure(state="disabled")
        elif "Clipboard" in choice or "剪贴板" in choice:
            self.cookie_val_var.set("")
            self.entry_cookie_val.configure(state="normal")
            self.entry_cookie_val.focus()
        else:
            self.cookie_val_var.set("")
            self.entry_cookie_val.configure(state="disabled")
            
    def browse_dir(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.outdir_var.set(dir_path)

    def toggle_pause(self):
        if self.is_paused:
            self.is_paused = False
            self.btn_pause.configure(text=self.t("pause"))
            self.pause_event.set()
        else:
            self.is_paused = True
            self.btn_pause.configure(text="▶ Resume")
            self.pause_event.clear()

    def stop_download(self):
        if messagebox.askyesno(self.t("confirm_title"), self.t("confirm_stop")):
            self.is_stopped = True
            self.is_paused = False
            self.pause_event.set() # Unblock if paused
            self.lbl_status.configure(text=self.t("stopping"))
            self.btn_stop.configure(state="disabled")

    def progress_hook(self, d):
        if self.is_stopped:
            raise ValueError("USER_STOPPED")
            
        if self.is_paused:
            self.after(0, lambda: self.lbl_status.configure(text=f"{self.t('paused_stat')}{Path(d.get('filename', '')).name}"))
            self.pause_event.wait()
            if self.is_stopped:
                raise ValueError("USER_STOPPED")

        if d['status'] == 'downloading':
            try:
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                speed = d.get('_speed_str', 'N/A').strip()
                # 提取实际的纯文件名 (处理有些特殊符号)
                filename = Path(d.get('filename', '')).name
                
                pct = 0.0
                if total and total > 0:
                    pct = downloaded / total
                    if pct > 1.0: pct = 1.0
                    if pct < 0.0: pct = 0.0
                
                def update_ui():
                    if not self.is_paused and not self.is_stopped:
                        concurrent = int(self.threads_var.get())
                        if concurrent <= 1:
                            self.progress_var.set(pct)
                            self.lbl_status.configure(text=f"{self.t('downloading')}{filename}{self.t('speed')}{speed}")
                        else:
                            self.lbl_status.configure(text=self.t("concurrent_dl"))
                    
                self.after(0, update_ui)
            except Exception:
                pass
        elif d['status'] == 'finished':
            self.downloaded_files_count += 1
            filename = Path(d.get('filename', '')).name
            if int(self.threads_var.get()) <= 1:
                self.after(0, lambda: self.lbl_status.configure(text=f"{self.t('finished')}{filename}{self.t('processing')}"))
                self.after(0, lambda: self.progress_var.set(1.0))

    def start_download(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning(self.t("warning"), self.t("enter_url"))
            return
            
        self.is_stopped = False
        self.is_paused = False
        self.pause_event.set()
        self.btn_pause.configure(state="normal", text=self.t("pause"))
        self.btn_stop.configure(state="normal", text=self.t("stop"))
        self.btn_download.configure(state="disabled", text="Downloading...", fg_color=self.default_btn_color, hover_color=self.default_btn_hover)
        self.lbl_status.configure(text=self.t("preparing"))
        self.progress_var.set(0)
        
        # clear generic logs for new download
        self.textbox_log.configure(state="normal")
        self.textbox_log.delete("1.0", "end")
        self.textbox_log.configure(state="disabled")
        
        # Start background thread
        threading.Thread(target=self._download_thread, args=(url,), daemon=True).start()
        
    def _download_thread(self, url):
        self.downloaded_files_count = 0
        try:
            log.info("=" * 60)
            log.info(f"{self.t('log_start')}{url}")
            log.info("=" * 60)
            
            # 1. 解析 Cookie
            cookie_src = self.cookie_src_var.get()
            cookie_val = self.cookie_val_var.get().strip()
            
            manager_kwargs = {}
            if "cookies.txt" in cookie_src:
                manager_kwargs["cookies_file"] = cookie_val
            elif "Clipboard" in cookie_src or "剪贴板" in cookie_src:
                manager_kwargs["cookie_str"] = cookie_val
            elif "Browser" in cookie_src or "浏览器" in cookie_src:
                browser = cookie_src.split(" ")[0].lower()
                manager_kwargs["browser"] = browser
                
            cookies = {}
            browser_name_for_opts = None
            if manager_kwargs:
                log.info(f"{self.t('log_cookie_try')} ({cookie_src})...")
                manager = CookieManager(**manager_kwargs)
                try:
                    cookies = manager.get()
                    log.info(f"{self.t('log_cookie_succ')}{len(cookies)}{self.t('log_cookie_succ2')}")
                except Exception as e:
                    log.warning(f"{self.t('log_cookie_fail')}{e}")
                
                # 如果是直接从浏览器提取，记录浏览器名供 yt-dlp 兜底
                if "browser" in manager_kwargs:
                    browser_name_for_opts = manager_kwargs["browser"]

            # 2. 生成下载任务
            platform = self.platform_var.get()
            output_dir = Path(self.outdir_var.get())
            quality = self.quality_var.get()
            
            tasks = []
            if platform == "Generic (YouTube/Bilibili etc.)":
                plugin = GenericYtdlpPlugin()
                tasks = plugin.get_download_tasks(
                    url_or_id=url,
                    output_dir=output_dir,
                    cookies=cookies or None,
                    quality=quality,
                    subtitle=self.subtitle_var.get(),
                    playlist_items=self.playlist_items_var.get() or None,
                    stop_check=lambda: self.is_stopped
                )
            elif platform == "Harvard (CS50)":
                plugin = HarvardPlugin()
                tasks = plugin.get_download_tasks(
                    url_or_id=url,
                    output_dir=output_dir,
                    cookies=cookies or None,
                    quality=quality,
                    stop_check=lambda: self.is_stopped
                )
            elif platform == "DeepLearning.AI":
                plugin = DeepLearningPlugin()
                weeks_str = self.weeks_var.get().strip()
                weeks = [int(w) for w in weeks_str.split()] if weeks_str else None
                tasks = plugin.get_download_tasks(
                    url_or_id=url,
                    output_dir=output_dir,
                    cookies=cookies or None, # Deeplearning needs them explicitly
                    weeks=weeks,
                    stop_check=lambda: self.is_stopped
                )
            elif platform == "Coursera":
                plugin = CourseraPlugin()
                tasks = plugin.get_download_tasks(
                    url_or_id=url,
                    output_dir=output_dir,
                    cookies=cookies or None,
                    quality=quality,
                    subtitle=self.subtitle_var.get(),
                    stop_check=lambda: self.is_stopped
                )
            elif platform == "KodeKloud":
                plugin = KodeKloudPlugin()
                tasks = plugin.get_download_tasks(
                    url_or_id=url,
                    output_dir=output_dir,
                    cookies=cookies or None,
                    quality=quality,
                    stop_check=lambda: self.is_stopped
                )
            elif platform == "Skills Google":
                plugin = SkillsGooglePlugin()
                tasks = plugin.get_download_tasks(
                    url_or_id=url,
                    output_dir=output_dir,
                    cookies=cookies or None,
                    quality=quality,
                    stop_check=lambda: self.is_stopped
                )

            # 3. 注入 GUI 需要的钩子和通用 Cookies
            for t in tasks:
                if getattr(t, "ignore_global_cookies", False):
                    continue
                if t.extra_opts is None:
                    t.extra_opts = {}
                
                # UI specific hooks
                t.extra_opts["logger"] = self.ytdlp_logger
                t.extra_opts["progress_hooks"] = [self.progress_hook]
                t.extra_opts["noprogress"] = True # let GUI handle progress bar
                t.extra_opts["quiet"] = False
                # 始终开启 verbose，交由我们的 YtdlpLogger 在输出时根据当前的动态日志级别控制，以实现秒切日志级别生效
                t.extra_opts["verbose"] = True
                
                # Cookie injection for yt-dlp layer
                if "cookies.txt" in cookie_src:
                    t.extra_opts["cookiefile"] = cookie_val
                elif browser_name_for_opts:
                    t.extra_opts["cookiesfrombrowser"] = (browser_name_for_opts,)
                    
                # Anti-bot
                if "extractor_args" not in t.extra_opts:
                    t.extra_opts["extractor_args"] = {}
                if "youtube" not in t.extra_opts["extractor_args"]:
                    t.extra_opts["extractor_args"]["youtube"] = {"player_client": ["web_creator", "tv", "ios", "web"]}

            # 4. 执行任务
            success_count = 0
            partial_count = 0
            has_error = False
            failed_tasks = []
            
            total_tasks = len(tasks)
            if total_tasks == 0:
                self.after(0, lambda: self.lbl_status.configure(text="No downloadable content found"))
                log.warning("No download tasks could be parsed.")
                return

            log.info(f"发现 {total_tasks} 个下载子任务，准备下载...")
            
            concurrent = int(self.threads_var.get())
            if concurrent <= 1:
                for i, task in enumerate(tasks):
                    if self.is_stopped:
                        log.warning("🚫 Queue execution aborted")
                        break
                        
                    display_name = "Resolving actual filename..." if "%(" in task.filename else task.filename
                    log.info(f"\n---> 开始执行任务 [{i+1}/{total_tasks}]: {display_name}")
                    self.after(0, lambda name=display_name: self.lbl_status.configure(text=f"即将开始: {name}"))
                    self.after(0, lambda: self.progress_var.set(0)) # reset progress
                    
                    try:
                        name, status = task.run()
                        if status == "success":
                            success_count += 1
                        elif status == "partial":
                            partial_count += 1
                            failed_tasks.append(display_name + " (Includes failed items)")
                        else:
                            failed_tasks.append(display_name)
                    except Exception as task_err:
                        if "USER_STOPPED" in str(task_err) or "yt_dlp" in str(task_err):
                            if self.is_stopped:
                                log.warning(f"🚫 任务已终止: {display_name}")
                                break
                        has_error = True
                        log.exception(f"❌ 任务 {display_name} 执行期间异常: {task_err}")
                        failed_tasks.append(display_name + " (Exception)")
            else:
                self.after(0, lambda: self.progressbar.configure(mode="indeterminate"))
                self.after(0, lambda: self.progressbar.start())
                
                with ThreadPoolExecutor(max_workers=concurrent) as executor:
                    futures = {executor.submit(task.run): (i, task) for i, task in enumerate(tasks, 1)}
                    for future in as_completed(futures):
                        # 检查中断。注意，如果有任务阻塞在请求或解析处，它需要通过内部钩子自行退出。
                        # 对于已经分配但是还没有执行的任务，我们无法完美取消，但我们可以记录。
                        i, task = futures[future]
                        display_name = "Resolving actual filename..." if "%(" in task.filename else task.filename
                        try:
                            name, status = future.result()
                            if status == "success":
                                success_count += 1
                                log.info(f"[{i}/{total_tasks}] ✅ {name}")
                            elif status == "partial":
                                partial_count += 1
                                failed_tasks.append(display_name + " (Includes failed items)")
                                log.info(f"[{i}/{total_tasks}] ⚠️ 部分/瑕疵: {name}")
                            else:
                                failed_tasks.append(display_name)
                                log.info(f"[{i}/{total_tasks}] ❌ {name}")
                        except Exception as task_err:
                            if "USER_STOPPED" in str(task_err) or "yt_dlp" in str(task_err):
                                if self.is_stopped:
                                    log.warning(f"🚫 子任务已终止: {display_name}")
                                    continue
                            has_error = True
                            log.exception(f"[{i}/{total_tasks}] ❌ 异常 ({display_name}): {task_err}")
                            failed_tasks.append(display_name + " (Exception)")
                            
                self.after(0, lambda: self.progressbar.stop())
                self.after(0, lambda: self.progressbar.configure(mode="determinate"))
                self.after(0, lambda: self.progress_var.set(1.0))
            
            if self.is_stopped:
                log.info("\n" + "=" * 60)
                log.info(f"🛑 下载已被用户提前手动停止。完成情况: {success_count} 成功。")
                log.info("=" * 60)
            else:
                log.info("\n" + "=" * 60)
                fails = len(tasks) - success_count - partial_count + partial_count
                log.info(self.t("log_success").format(success_count, fails, self.downloaded_files_count))
                if failed_tasks:
                    log.warning(f"⚠️ The following tasks failed to download completely:")
                    error_msg_lines = []
                    for ftask in failed_tasks:
                        log.warning(f"  - {ftask}")
                        error_msg_lines.append(f"• {ftask}")
                    log.info("=" * 60)
                    
                    # 弹窗强提示用户
                    max_display = 15
                    display_text = "\n".join(error_msg_lines[:max_display])
                    if len(error_msg_lines) > max_display:
                        display_text += f"\n...以及另外 {len(error_msg_lines) - max_display} 个任务"
                        
                    self.after(0, lambda: messagebox.showwarning(
                        "Some tasks failed to download",
                        f"在刚才的批量队列中，有 {len(error_msg_lines)} 个任务无法完整下载：\n\n{display_text}\n\n详情请查看上方日志区域。"
                    ))
                else:
                    log.info("=" * 60)

        except Exception as e:
            if not self.is_stopped:
                has_error = True
                log.exception(f"❌ 下载过程发生未知错误: {e}")
            
        finally:
            # 根据状态恢复按钮颜色和文字
            def restore_btn():
                self.btn_pause.configure(state="disabled")
                self.btn_stop.configure(state="disabled")
                if self.is_stopped:
                    self.btn_download.configure(state="normal", text="Terminated (Click to restart)", fg_color="#C62828", hover_color="#b71c1c")
                    self.lbl_status.configure(text=f"已手动打断。已完成 {success_count} 个任务。")
                elif has_error:
                    self.btn_download.configure(state="normal", text="Crashed (Click to retry)", fg_color="#C62828", hover_color="#b71c1c")
                    self.lbl_status.configure(text="程序抛出严重异常，请检查上方日志。")
                elif success_count == len(tasks) and len(tasks) > 0:
                    self.btn_download.configure(state="normal", text="下载成功！(点击再次发车)", fg_color="#2E7D32", hover_color="#1B5E20")
                    self.lbl_status.configure(text="全部任务完美处理完毕！")
                elif partial_count > 0 or (success_count > 0 and success_count < len(tasks)):
                    self.btn_download.configure(state="normal", text="包含失败项 (提示在上方)", fg_color="#EF6C00", hover_color="#E65100")
                    self.lbl_status.configure(text=f"成 {success_count} 瑕 {partial_count} 败 {len(tasks) - success_count - partial_count}。")
                elif success_count == 0 and len(tasks) > 0:
                    self.btn_download.configure(state="normal", text="全军覆没 (点击重传)", fg_color="#C62828", hover_color="#b71c1c")
                    self.lbl_status.configure(text="所有下载任务均已失败。")
                else:
                    self.btn_download.configure(state="normal", text=self.t("start"), fg_color=self.default_btn_color, hover_color=self.default_btn_hover)
                    
            self.after(0, restore_btn)

def main():
    app = VideoDownloaderApp()
    app.mainloop()

if __name__ == "__main__":
    main()
