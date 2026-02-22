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

class VideoDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # State vars
        self.is_paused = False
        self.is_stopped = False
        self.pause_event = threading.Event()
        self.pause_event.set() # Set initial state to not paused

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
        
        self.lbl_url = ctk.CTkLabel(self.frame_url, text="Video/Course URL:")
        self.lbl_url.grid(row=0, column=0, padx=10, pady=10)
        
        self.entry_url = ctk.CTkEntry(self.frame_url, placeholder_text="https://...")
        self.entry_url.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # 2. 核心配置区 (平台 & 动态配置 & 环境)
        self.frame_config = ctk.CTkFrame(self)
        self.frame_config.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.frame_config.grid_columnconfigure(1, weight=1)
        
        # Platform Selection
        self.lbl_platform = ctk.CTkLabel(self.frame_config, text="Platform:")
        self.lbl_platform.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.platform_var = ctk.StringVar(value="Generic (YouTube/Bilibili etc.)")
        self.combo_platform = ctk.CTkComboBox(self.frame_config, variable=self.platform_var,
            values=["Generic (YouTube/Bilibili etc.)", "Harvard (CS50)", "DeepLearning.AI", "Coursera", "KodeKloud", "Skills Google"],
            command=self.on_platform_change)
        self.combo_platform.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Quality Selection
        self.lbl_quality = ctk.CTkLabel(self.frame_config, text="Max Quality:")
        self.lbl_quality.grid(row=0, column=2, padx=10, pady=10, sticky="w")
        
        self.quality_var = ctk.StringVar(value="best")
        self.combo_quality = ctk.CTkComboBox(self.frame_config, variable=self.quality_var,
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
        self.lbl_outdir = ctk.CTkLabel(self.frame_config, text="Output Dir:")
        self.lbl_outdir.grid(row=2, column=0, padx=10, pady=10, sticky="w")
        
        self.outdir_var = ctk.StringVar(value=str(Path("./downloads").absolute()))
        self.entry_outdir = ctk.CTkEntry(self.frame_config, textvariable=self.outdir_var)
        self.entry_outdir.grid(row=2, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        
        self.btn_browse = ctk.CTkButton(self.frame_config, text="Browse...", command=self.browse_dir, width=60)
        self.btn_browse.grid(row=2, column=3, padx=10, pady=10)
        
        self.lbl_cookie = ctk.CTkLabel(self.frame_config, text="Cookies:")
        self.lbl_cookie.grid(row=3, column=0, padx=10, pady=10, sticky="w")
        
        self.cookie_src_var = ctk.StringVar(value="None (No login)")
        self.combo_cookie_src = ctk.CTkComboBox(self.frame_config, variable=self.cookie_src_var,
            values=["None (No login)", "Chrome Browser", "Edge Browser", "Firefox Browser", "Brave Browser", "Clipboard (Paste text)", "Select cookies.txt..."],
            command=self.on_cookie_src_change)
        self.combo_cookie_src.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        
        self.cookie_val_var = ctk.StringVar()
        self.entry_cookie_val = ctk.CTkEntry(self.frame_config, textvariable=self.cookie_val_var, state="disabled")
        self.entry_cookie_val.grid(row=3, column=2, columnspan=2, padx=10, pady=10, sticky="ew")

        # Log Level
        self.lbl_loglevel = ctk.CTkLabel(self.frame_config, text="Log Level:")
        self.lbl_loglevel.grid(row=4, column=0, padx=10, pady=10, sticky="w")
        
        self.loglevel_var = ctk.StringVar(value="INFO")
        self.combo_loglevel = ctk.CTkComboBox(self.frame_config, variable=self.loglevel_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            command=self.on_loglevel_change)
        self.combo_loglevel.grid(row=4, column=1, padx=10, pady=10, sticky="ew")

        # Thread count
        self.lbl_threads = ctk.CTkLabel(self.frame_config, text="Concurrency (Threads):")
        self.lbl_threads.grid(row=4, column=2, padx=10, pady=10, sticky="w")
        
        self.threads_var = ctk.StringVar(value="1")
        self.combo_threads = ctk.CTkComboBox(self.frame_config, variable=self.threads_var,
            values=["1", "2", "3", "4", "5"])
        self.combo_threads.grid(row=4, column=3, padx=10, pady=10, sticky="ew")

        # 3. 进度与日志区
        self.frame_log = ctk.CTkFrame(self)
        self.frame_log.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.frame_log.grid_columnconfigure(0, weight=1)
        self.frame_log.grid_rowconfigure(0, weight=1)
        
        self.textbox_log = ctk.CTkTextbox(self.frame_log, state="disabled", wrap="word", font=("Consolas", 12))
        self.textbox_log.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        self.lbl_status = ctk.CTkLabel(self.frame_log, text="Waiting...", font=("", 13), text_color="gray", anchor="w")
        self.lbl_status.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        
        self.progress_var = ctk.DoubleVar(value=0)
        self.progressbar = ctk.CTkProgressBar(self.frame_log, variable=self.progress_var)
        self.progressbar.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.progressbar.set(0) # initialize to 0
        
        # 4. 操作区
        self.frame_actions = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_actions.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.frame_actions.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.btn_download = ctk.CTkButton(self.frame_actions, text="Start Download", height=45, font=("", 16, "bold"), command=self.start_download)
        self.btn_download.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        self.btn_pause = ctk.CTkButton(self.frame_actions, text="⏸ Pause", height=45, font=("", 16, "bold"), command=self.toggle_pause, state="disabled")
        self.btn_pause.grid(row=0, column=1, padx=10, sticky="ew")
        
        self.btn_stop = ctk.CTkButton(self.frame_actions, text="⏹ Stop", height=45, font=("", 16, "bold"), command=self.stop_download, state="disabled", fg_color="#C62828", hover_color="#b71c1c")
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
                if logging.getLogger().level <= logging.DEBUG:
                    log.debug(msg)
            def info(self, msg):
                # ignore noise unless in DEBUG mode
                if logging.getLogger().level > logging.DEBUG:
                    if "frag" in msg.lower() or "eta" in msg.lower() or "[download]" in msg:
                        return
                log.info(msg)
            def warning(self, msg):
                log.warning(msg)
            def error(self, msg):
                log.error(msg)
        self.ytdlp_logger = YtdlpLogger()

        self.on_loglevel_change(self.loglevel_var.get())
        
        self.on_platform_change(self.platform_var.get())
        
        log.info("欢迎使用 VideoDownloader GUI 版本！由于部分环境缺少配置，在启动期间如有卡顿属于正常现象。")

    def build_dynamic_options(self):
        # Clear dynamic frame
        for widget in self.frame_dynamic.winfo_children():
            widget.destroy()
            
        platform = self.platform_var.get()
        
        if platform == "Generic (YouTube/Bilibili etc.)":
            self.lbl_quality.grid()
            self.combo_quality.grid()
            
            lbl1 = ctk.CTkLabel(self.frame_dynamic, text="播放列表范围:")
            lbl1.grid(row=0, column=0, padx=10, pady=5, sticky="w")
            ent1 = ctk.CTkEntry(self.frame_dynamic, textvariable=self.playlist_items_var, placeholder_text="如 1-25 或 1,3,5 (留空下载所有)")
            ent1.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
            
            chk1 = ctk.CTkCheckBox(self.frame_dynamic, text="下载字幕", variable=self.subtitle_var)
            chk1.grid(row=0, column=2, padx=10, pady=5, sticky="w")
            
        elif platform == "Harvard (CS50)":
            self.lbl_quality.grid()
            self.combo_quality.grid()
            
            lbl1 = ctk.CTkLabel(self.frame_dynamic, text="说明: Harvard 模式支持自动探测播放列表。将全自动提取指定页面或\n播放列表下的所有 YouTube 视频、MP4 直链、PDF 讲义与源码包素材。")
            lbl1.grid(row=0, column=0, columnspan=4, padx=10, pady=5, sticky="w")
            
        elif platform == "DeepLearning.AI":
            self.lbl_quality.grid_remove() # Deeplearning ai overrides quality
            self.combo_quality.grid_remove()
            
            lbl1 = ctk.CTkLabel(self.frame_dynamic, text="指定 Week(s):")
            lbl1.grid(row=0, column=0, padx=10, pady=5, sticky="w")
            ent1 = ctk.CTkEntry(self.frame_dynamic, textvariable=self.weeks_var, placeholder_text="如: 1 2 (空格分隔, 留空下载全部)")
            ent1.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
            
        elif platform == "Coursera":
            self.lbl_quality.grid()
            self.combo_quality.grid()
            
            chk1 = ctk.CTkCheckBox(self.frame_dynamic, text="下载字幕", variable=self.subtitle_var)
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
        if choice == "Select cookies.txt...":
            file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
            if file_path:
                self.cookie_val_var.set(file_path)
                self.entry_cookie_val.configure(state="normal")
            else:
                self.cookie_src_var.set("None (No login)")
                self.cookie_val_var.set("")
                self.entry_cookie_val.configure(state="disabled")
        elif choice == "Clipboard (Paste text)":
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
            self.btn_pause.configure(text="⏸ Pause")
            self.pause_event.set()
        else:
            self.is_paused = True
            self.btn_pause.configure(text="▶ Resume")
            self.pause_event.clear()

    def stop_download(self):
        if messagebox.askyesno("Confirmation", "Stop current download and cancel queued tasks?"):
            self.is_stopped = True
            self.is_paused = False
            self.pause_event.set() # Unblock if paused
            self.lbl_status.configure(text="Force stopping, please wait...")
            self.btn_stop.configure(state="disabled")

    def progress_hook(self, d):
        if self.is_stopped:
            raise ValueError("USER_STOPPED")
            
        if self.is_paused:
            self.after(0, lambda: self.lbl_status.configure(text=f"已暂停: {Path(d.get('filename', '')).name}"))
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
                            self.lbl_status.configure(text=f"正在下载: {filename}   |   速度: {speed}")
                        else:
                            self.lbl_status.configure(text=f"Concurrent downloading... Check logs")
                    
                self.after(0, update_ui)
            except Exception:
                pass
        elif d['status'] == 'finished':
            filename = Path(d.get('filename', '')).name
            if int(self.threads_var.get()) <= 1:
                self.after(0, lambda: self.lbl_status.configure(text=f"已下载完成: {filename}，正在合并或处理..."))
                self.after(0, lambda: self.progress_var.set(1.0))

    def start_download(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter URL or Course Slug")
            return
            
        self.is_stopped = False
        self.is_paused = False
        self.pause_event.set()
        self.btn_pause.configure(state="normal", text="⏸ Pause")
        self.btn_stop.configure(state="normal", text="⏹ Stop")
        self.btn_download.configure(state="disabled", text="Downloading...", fg_color=self.default_btn_color, hover_color=self.default_btn_hover)
        self.lbl_status.configure(text="Preparing...")
        self.progress_var.set(0)
        
        # clear generic logs for new download
        self.textbox_log.configure(state="normal")
        self.textbox_log.delete("1.0", "end")
        self.textbox_log.configure(state="disabled")
        
        # Start background thread
        threading.Thread(target=self._download_thread, args=(url,), daemon=True).start()
        
    def _download_thread(self, url):
        try:
            log.info("=" * 60)
            log.info(f"🚀 开始下载任务: {url}")
            log.info("=" * 60)
            
            # 1. 解析 Cookie
            cookie_src = self.cookie_src_var.get()
            cookie_val = self.cookie_val_var.get().strip()
            
            manager_kwargs = {}
            if cookie_src == "Select cookies.txt...":
                manager_kwargs["cookies_file"] = cookie_val
            elif cookie_src == "Clipboard (Paste text)":
                manager_kwargs["cookie_str"] = cookie_val
            elif "浏览器" in cookie_src:
                browser = cookie_src.split(" ")[0].lower()
                manager_kwargs["browser"] = browser
                
            cookies = {}
            browser_name_for_opts = None
            if manager_kwargs:
                log.info(f"正在尝试获取 Cookie ({cookie_src})...")
                manager = CookieManager(**manager_kwargs)
                try:
                    cookies = manager.get()
                    log.info(f"成功获取到 {len(cookies)} 条 Cookie 记录。")
                except Exception as e:
                    log.warning(f"获取 Cookie 失败: {e}")
                
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
                
                # Cookie injection for yt-dlp layer
                if cookie_src == "Select cookies.txt...":
                    t.extra_opts["cookiefile"] = cookie_val
                elif browser_name_for_opts:
                    t.extra_opts["cookiesfrombrowser"] = (browser_name_for_opts,)
                    
                # Anti-bot
                if "extractor_args" not in t.extra_opts:
                    t.extra_opts["extractor_args"] = {}
                if "youtube" not in t.extra_opts["extractor_args"]:
                    t.extra_opts["extractor_args"]["youtube"] = {}

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
                log.info(f"✅ 队列执行完毕！成功 {success_count}，部分/瑕疵 {partial_count}，完全失败 {len(tasks) - success_count - partial_count}。")
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
                        f"在刚才的批量队列中，有 {len(error_msg_lines)} 个任务无法完整下载：\n\n{display_text}\n\n详情请查看左侧日志区域。"
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
                    self.btn_download.configure(state="normal", text="Start Download", fg_color=self.default_btn_color, hover_color=self.default_btn_hover)
                    
            self.after(0, restore_btn)

def main():
    app = VideoDownloaderApp()
    app.mainloop()

if __name__ == "__main__":
    main()
