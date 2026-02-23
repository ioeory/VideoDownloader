import re

def process():
    with open("videodownloader/gui/app.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Inject full i18n
    i18n_dict = """        self.current_lang = "en"
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
                "log_starting_ytdlp": "⏳ Starting yt-dlp queue for {} (URL: {})",
                "log_download_complete": "✅ Download complete: {} (URL: {})",
                "log_start_requests": "⏳ Starting download: {} (URL: {})",
                "speed": "   |   Speed: ",
                "concurrent_dl": "Concurrent downloading... Check logs",
                "processing": ", processing...",
                "finished": "Finished: ",
                "stat_starting_task": "[{}/{}] Starting: {}",
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
                "log_success": "✅ Queue execution finished! Success: ",
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
                "log_starting_ytdlp": "⏳ 正在启动 yt-dlp 队列: {} (URL: {})",
                "log_download_complete": "✅ 下载完成: {} (URL: {})",
                "log_start_requests": "⏳ 开始下载: {} (URL: {})",
                "speed": "   |   速度: ",
                "concurrent_dl": "并发下载中 (多线程活动)... 请查看左侧日志",
                "processing": "，正在合并处理...",
                "finished": "已下载完成: ",
                "stat_starting_task": "[{}/{}] 正在开始: {}",
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
                "log_success": "✅ 队列执行完毕！成功 ",
                "log_partial": "瑕疵 ",
                "log_failed": "失败 "
            }
        }"""
    
    # Insert i18n
    pos = content.find("self.pause_event.set()")
    insert_pos = content.find("\n", pos) + 1
    content = content[:insert_pos] + i18n_dict + "\n" + content[insert_pos:]
    
    # 2. Add language methods
    lang_methods = """
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
"""
    build_idx = content.find("    def build_dynamic_options(self):")
    content = content[:build_idx] + lang_methods + "\n" + content[build_idx:]
    
    # 3. Add Language toggle button UI component
    url_entry_idx = content.find('self.entry_url.grid(row=0, column=1, padx=10, pady=10, sticky="ew")')
    url_entry_end = content.find('\n', url_entry_idx) + 1
    btn_code = '        self.btn_lang = ctk.CTkButton(self.frame_url, text=self.t("lang_toggle"), width=120, command=self.toggle_language, fg_color="#455A64", hover_color="#37474F")\n        self.btn_lang.grid(row=0, column=2, padx=10, pady=10)\n'
    content = content[:url_entry_end] + btn_code + content[url_entry_end:]

    # Call update_ui_texts at initialization
    init_end = content.find("self.on_platform_change(self.platform_var.get())")
    content = content[:init_end] + "self.update_ui_texts()\n        " + content[init_end:]

    # Replace hardcoded GUI initializations 
    content = content.replace('text="Video/Course URL:"', 'text=self.t("url")')
    content = content.replace('text="Platform:"', 'text=self.t("platform")')
    content = content.replace('text="Max Quality:"', 'text=self.t("quality")')
    content = content.replace('text="Output Dir:"', 'text=self.t("outdir")')
    content = content.replace('text="Browse..."', 'text=self.t("browse")')
    content = content.replace('text="Cookies:"', 'text=self.t("cookies")')
    content = content.replace('text="Log Level:"', 'text=self.t("loglevel")')
    content = content.replace('text="Concurrency (Threads):"', 'text=self.t("threads")')
    content = content.replace('text="Waiting..."', 'text=self.t("waiting")')
    content = content.replace('text="Start Download"', 'text=self.t("start")')
    content = content.replace('text="⏸ Pause"', 'text=self.t("pause")')
    content = content.replace('text="⏹ Stop"', 'text=self.t("stop")')
    content = content.replace('text="播放列表范围:"', 'text=self.t("playlist_range")')
    content = content.replace('placeholder_text="如 1-25 或 1,3,5 (留空下载所有)"', 'placeholder_text=self.t("playlist_ph")')
    content = content.replace('text="下载字幕"', 'text=self.t("subtitles")')
    content = content.replace('text="说明: Harvard 模式支持自动探测播放列表。将全自动提取指定页面或\\n播放列表下的所有 YouTube 视频、MP4 直链、PDF 讲义与源码包素材。"', 'text=self.t("harvard_info")')
    content = content.replace('text="指定 Week(s):"', 'text=self.t("weeks")')
    content = content.replace('placeholder_text="如: 1 2 (空格分隔, 留空下载全部)"', 'placeholder_text=self.t("weeks_ph")')
    
    # Handle the combo box instantiation for cookie options natively 
    combo_str = 'values=["None (No login)", "Chrome Browser", "Edge Browser", "Firefox Browser", "Brave Browser", "Clipboard (Paste text)", "Select cookies.txt..."],'
    combo_str_new = 'values=[self.t(\'cookie_none\'), self.t(\'cookie_chrome\'), self.t(\'cookie_edge\'), self.t(\'cookie_firefox\'), self.t(\'cookie_brave\'), self.t(\'cookie_clipboard\'), self.t(\'cookie_file\')],'
    content = content.replace(combo_str, combo_str_new)
    
    # Fix the file path logic for Cookie Select
    content = content.replace('if choice == "Select cookies.txt...":', 'if "cookies.txt" in choice:')
    content = content.replace('self.cookie_src_var.set("None (No login)")', 'self.cookie_src_var.set(self.t("cookie_none"))')
    content = content.replace('if cookie_src == "Select cookies.txt...":', 'if "cookies.txt" in cookie_src:')
    content = content.replace('elif cookie_src == "Clipboard (Paste text)":', 'elif "Clipboard" in cookie_src or "剪贴板" in cookie_src:')
    content = content.replace('elif "Browser" in cookie_src:', 'elif "Browser" in cookie_src or "浏览器" in cookie_src:')
    content = content.replace('elif "浏览器" in cookie_src:', 'elif "Browser" in cookie_src or "浏览器" in cookie_src:')

    # Replaces some logs and statuses
    content = content.replace('log.info("欢迎使用 VideoDownloader GUI 版本！由于部分环境缺少配置，在启动期间如有卡顿属于正常现象。")', 'log.info(self.t("welcome"))')
    content = content.replace('messagebox.askyesno("Confirmation", "Stop current download and cancel queued tasks?")', 'messagebox.askyesno(self.t("confirm_title"), self.t("confirm_stop"))')
    content = content.replace('self.lbl_status.configure(text="Force stopping, please wait...")', 'self.lbl_status.configure(text=self.t("stopping"))')
    content = content.replace('messagebox.showwarning("Warning", "Please enter URL or Course Slug")', 'messagebox.showwarning(self.t("warning"), self.t("enter_url"))')
    
    # Dynamic GUI updates
    content = content.replace('text=f"已暂停: {Path(d.get(\'filename\', \'\')).name}"', 'text=f"{self.t(\'paused_stat\')}{Path(d.get(\'filename\', \'\')).name}"')
    content = content.replace('text=f"正在下载: {filename}   |   速度: {speed}"', 'text=f"{self.t(\'downloading\')}{filename}{self.t(\'speed\')}{speed}"')
    content = content.replace('text=f"Concurrent downloading... Check logs"', 'text=self.t("concurrent_dl")')
    content = content.replace('text=f"已下载完成: {filename}，正在合并或处理..."', 'text=f"{self.t(\'finished\')}{filename}{self.t(\'processing\')}"')
    
    content = content.replace('self.btn_pause.configure(state="normal", text="⏸ Pause")', 'self.btn_pause.configure(state="normal", text=self.t("pause"))')
    content = content.replace('self.btn_stop.configure(state="normal", text="⏹ Stop")', 'self.btn_stop.configure(state="normal", text=self.t("stop"))')
    content = content.replace('self.lbl_status.configure(text="Preparing...")', 'self.lbl_status.configure(text=self.t("preparing"))')
    content = content.replace('log.info(f"🚀 开始下载任务: {url}")', 'log.info(f"{self.t(\'log_start\')}{url}")')
    
    content = content.replace('log.info(f"正在尝试获取 Cookie ({cookie_src})...")', 'log.info(f"{self.t(\'log_cookie_try\')} ({cookie_src})...")')
    content = content.replace('log.info(f"成功获取到 {len(cookies)} 条 Cookie 记录。")', 'log.info(f"{self.t(\'log_cookie_succ\')}{len(cookies)}{self.t(\'log_cookie_succ2\')}")')
    content = content.replace('log.warning(f"获取 Cookie 失败: {e}")', 'log.warning(f"{self.t(\'log_cookie_fail\')}{e}")')

    with open("videodownloader/gui/app.py", "w", encoding="utf-8") as f:
        f.write(content)

process()
print("Cleanly rebuilt i18n without any broken emojis or fonts in fallback mode.")
