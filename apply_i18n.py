import re

with open("videodownloader/gui/app.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add current_lang and translation dict inside __init__
init_injection = """        # Language State
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
                "pause": "⏸ Pause",
                "resume": "▶ Resume",
                "stop": "⏹ Stop",
                "playlist_range": "Playlist Items (e.g. 1-5, 8):",
                "playlist_ph": "e.g. 1-25 or 1,3,5 (blank for all)",
                "subtitles": "Download Subtitles (.vtt/.srt)",
                "harvard_info": "Info: Harvard mode auto-detects playlists and downloads videos, PDFs, and assets.",
                "weeks": "Specific Week(s):",
                "weeks_ph": "e.g. 1 2 (space separated, blank for all)",
                "welcome": "Welcome to VideoDownloader GUI! Stuttering during startup is normal.",
                "lang_toggle": "🌐 中文"
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
                "pause": "⏸ 暂停",
                "resume": "▶ 继续",
                "stop": "⏹ 停止",
                "playlist_range": "播放列表范围:",
                "playlist_ph": "如 1-25 或 1,3,5 (留空下载所有)",
                "subtitles": "下载字幕",
                "harvard_info": "说明: Harvard 模式支持自动探测播放列表。将全自动提取指定页面或\\n播放列表下的所有 YouTube 视频、MP4 直链、PDF 讲义与源码包素材。",
                "weeks": "指定 Week(s):",
                "weeks_ph": "如: 1 2 (空格分隔, 留空下载全部)",
                "welcome": "欢迎使用 VideoDownloader GUI 版本！由于部分环境缺少配置，在启动期间如有卡顿属于正常现象。",
                "lang_toggle": "🌐 English"
            }
        }

"""

# target __init__ specifically
init_pos = text.find("        self.pause_event = threading.Event()")
text = text[:init_pos] + init_injection + text[init_pos:]

# 2. Add language methods just before build_dynamic_options
methods_injection = """
    def t(self, key):
        return self.i18n[self.current_lang].get(key, key)

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
        
        # We only update if it is in default resting states, avoid overwriting dynamic status
        if self.btn_download.cget("text") in ["Start Download", "开始下载"]:
            self.btn_download.configure(text=self.t("start"))
        if self.btn_pause.cget("text") in ["⏸ Pause", "⏸ 暂停"]:
            self.btn_pause.configure(text=self.t("pause"))
        elif self.btn_pause.cget("text") in ["▶ Resume", "▶ 继续"]:
            self.btn_pause.configure(text=self.t("resume"))
        if self.btn_stop.cget("text") in ["⏹ Stop", "⏹ 停止", "Force stopping, please wait...", "正在强制停止，请稍候..."]:
            self.btn_stop.configure(text=self.t("stop"))
            
        if hasattr(self, 'btn_lang'):
            self.btn_lang.configure(text=self.t("lang_toggle"))
        
        if self.lbl_status.cget("text") in ["Waiting...", "等待下载..."]:
            self.lbl_status.configure(text=self.t("waiting"))
"""

build_idx = text.find("    def build_dynamic_options(self):")
text = text[:build_idx] + methods_injection + "\n" + text[build_idx:]

# 3. Add Language Button in frame_url
url_entry_idx = text.find('self.entry_url.grid(row=0, column=1, padx=10, pady=10, sticky="ew")')
url_entry_end = url_entry_idx + len('self.entry_url.grid(row=0, column=1, padx=10, pady=10, sticky="ew")')
btn_code = """
        self.btn_lang = ctk.CTkButton(self.frame_url, text="🌐 中文", width=80, command=self.toggle_language, fg_color="#455A64", hover_color="#37474F")
        self.btn_lang.grid(row=0, column=2, padx=10, pady=10)
"""
text = text[:url_entry_end] + btn_code + text[url_entry_end:]

# 4. Modify build_dynamic_options text to use self.t
text = text.replace('text="播放列表范围 (例: 1-5, 8):"', 'text=self.t("playlist_range")')
text = text.replace('placeholder_text="留空则默认下载全部"', 'placeholder_text=self.t("playlist_ph")')
text = text.replace('text="下载字幕 (.vtt/.srt)"', 'text=self.t("subtitles")')
text = text.replace('text="说明: Harvard 模式支持自动探测播放列表。将全自动提取指定页面或\\n播放列表下的所有 YouTube 视频、MP4 直链、PDF 讲义与源码包素材。"', 'text=self.t("harvard_info")')
text = text.replace('text="指定 周/章 (例: 1 2 4):"', 'text=self.t("weeks")')
text = text.replace('text="指定周卡 (例: 1 2 4):"', 'text=self.t("weeks")')
text = text.replace('placeholder_text="空格分隔, 留空则默认下载全部"', 'placeholder_text=self.t("weeks_ph")')

# 5. Finally, inject self.update_ui_texts() at end of init
# Replace self.on_platform_change(self.platform_var.get()) in init logic with update_ui_texts()
plat_change_init_idx = text.find("self.on_platform_change(self.platform_var.get())")
text = text[:plat_change_init_idx] + "self.update_ui_texts()\n        " + text[plat_change_init_idx:]

# 6. Make log english wrapper work for the welcome message
text = text.replace('log.info("欢迎使用 VideoDownloader GUI 版本！由于部分环境缺少配置，在启动期间如有卡顿属于正常现象。")', 'log.info(self.t("welcome"))')

# 7. Apply translation substitution for common hardcoded GUI display parts and logs
substitutions = {
    # start_download checks
    'messagebox.showwarning("警告", "请输入 URL 或 Course Slug")': 'messagebox.showwarning("Warning", "Please enter URL or Course Slug")',
    # status labels
    'self.lbl_status.configure(text="正在下载...")': 'self.lbl_status.configure(text="Downloading...")',
    'self.lbl_status.configure(text="准备下载...")': 'self.lbl_status.configure(text="Preparing download...")',
    'self.lbl_status.configure(text="正在强制停止，请稍候...")': 'self.lbl_status.configure(text="Force stopping, please wait...")',
    'self.lbl_status.configure(text="未找到需要下载的课时内容")': 'self.lbl_status.configure(text="No downloadable content found")',
    'self.lbl_status.configure(text=f"已手动打断。已完成 {success_count} 个任务。")': 'self.lbl_status.configure(text=f"Manually interrupted. Completed {success_count} tasks.")',
    'self.lbl_status.configure(text="程序抛出严重异常，请检查上方日志。")': 'self.lbl_status.configure(text="Execution exception, check logs.")',
    'self.lbl_status.configure(text="全部任务完美处理完毕！")': 'self.lbl_status.configure(text="All tasks have been processed!")',
    'self.lbl_status.configure(text=f"成 {success_count} 瑕 {partial_count} 败 {len(tasks) - success_count - partial_count}。")': 'self.lbl_status.configure(text=f"Success: {success_count} | Partial: {partial_count} | Failed: {len(tasks) - success_count - partial_count}")',
    'self.lbl_status.configure(text="所有下载任务均已失败。")': 'self.lbl_status.configure(text="All tasks failed.")',
    'self.lbl_status.configure(text=f"已暂停: {Path(d.get(\'filename\', \'\')).name}")': 'self.lbl_status.configure(text=f"Paused: {Path(d.get(\'filename\', \'\')).name}")',
    'self.lbl_status.configure(text=f"即将开始: {name}")': 'self.lbl_status.configure(text=f"Starting soon: {name}")',
    'self.lbl_status.configure(text=f"正在下载: {filename}   |   速度: {speed}")': 'self.lbl_status.configure(text=f"Downloading: {filename}   |   Speed: {speed}")',
    'self.lbl_status.configure(text=f"并发下载中 (多线程活动)... 请查看左侧日志")': 'self.lbl_status.configure(text="Concurrent downloading... Check logs")',
    'self.lbl_status.configure(text=f"已下载完成: {filename}，正在合并或处理...")': 'self.lbl_status.configure(text=f"Finished: {filename}, processing...")',

    # Buttons text end of processing
    'text="下载已终止 (点击重来)"': 'text="Terminated (Click to restart)"',
    'text="下载崩溃 (点击重试)"': 'text="Crashed (Click to retry)"',
    'text="下载成功！(点击再次发车)"': 'text="✅ All Completed (Click to restart)"',
    'text="包含失败项 (提示在上方)"': 'text="Contains failed tasks (Check logs)"',
    'text="全军覆没 (点击重传)"': 'text="All failed (Click to retry)"',
    
    # Dialogs
    'messagebox.askyesno("确认", "确定要停止当前下载(会取消后续任务)吗？")': 'messagebox.askyesno("Confirm", "Are you sure you want to stop the current download? (Queued tasks will be cancelled)")',
    'messagebox.showwarning(\n                        "有任务未能成功下载",\n                        f"在刚才的批量队列中，有 {len(error_msg_lines)} 个任务无法完整下载：\\n\\n{display_text}\\n\\n详情请查看左侧日志区域。"\n                    )': 'messagebox.showwarning("Warning", f"In the recent batch queue, {len(error_msg_lines)} tasks failed:\\n\\n{display_text}\\n\\nCheck logs for details.")',

    # Logs
    'log.warning("没有解析出任何下载任务。")': 'log.warning("No download tasks could be parsed.")',
    'log.info(f"发现 {total_tasks} 个下载子任务，准备下载...")': 'log.info(f"Found {total_tasks} sub-tasks, preparing download...")',
    'log.warning("🚫 队列执行已中止")': 'log.warning("🚫 Queue execution aborted")',
    '"解析真实文件名中..." if "%(" in task.filename else task.filename': '"Resolving actual filename..." if "%(" in task.filename else task.filename',
    'log.info(f"\\n---> 开始执行任务 [{i+1}/{total_tasks}]: {display_name}")': 'log.info(f"\\n---> Starting task [{i+1}/{total_tasks}]: {display_name}")',
    'failed_tasks.append(display_name + " (包含失败项)")': 'failed_tasks.append(display_name + " (Includes failed items)")',
    'log.warning(f"🚫 任务已终止: {display_name}")': 'log.warning(f"🚫 Task terminated: {display_name}")',
    'log.exception(f"❌ 任务 {display_name} 执行期间异常: {task_err}")': 'log.exception(f"❌ Task {display_name} exception: {task_err}")',
    'failed_tasks.append(display_name + " (异常)")': 'failed_tasks.append(display_name + " (Exception)")',
    'log.info(f"[{i}/{total_tasks}] ⚠️ 部分/瑕疵: {name}")': 'log.info(f"[{i}/{total_tasks}] ⚠️ Partial: {name}")',
    'log.warning(f"🚫 子任务已终止: {display_name}")': 'log.warning(f"🚫 Sub-task terminated: {display_name}")',
    'log.exception(f"[{i}/{total_tasks}] ❌ 异常 ({display_name}): {task_err}")': 'log.exception(f"[{i}/{total_tasks}] ❌ Exception ({display_name}): {task_err}")',
    'log.info(f"🛑 下载已被用户提前手动停止。完成情况: {success_count} 成功。")': 'log.info(f"🛑 Download manually stopped. Completions: {success_count} successful.")',
    'log.info(f"✅ 队列执行完毕！成功 {success_count}，部分/瑕疵 {partial_count}，完全失败 {len(tasks) - success_count - partial_count}。")': 'log.info(f"✅ Queue execution finished! Success: {success_count}, Partial: {partial_count}, Failed: {len(tasks) - success_count - partial_count}.")',
    'log.warning(f"⚠️ 以下任务未能完整下载，请检查其页面状态：")': 'log.warning("⚠️ The following tasks failed to download completely:")',
    'log.exception(f"❌ 下载过程发生未知错误: {e}")': 'log.exception(f"❌ Unknown error occurred: {e}")',
    
    # Static texts translated globally via python replace
    '"VideoDownloader — 通用视频下载器"': '"VideoDownloader - Universal Video Downloader"',
    '"视频/课程 URL:"': '"Video/Course URL:"',
    '"下载平台:"': '"Platform:"',
    '"最高画质:"': '"Max Quality:"',
    '"输出目录:"': '"Output Dir:"',
    '"浏览..."': '"Browse..."',
    '"Cookies 来源:"': '"Cookies:"',
    '"日志级别:"': '"Log Level:"',
    '"并发线程:"': '"Concurrency (Threads):"',
    '"等待下载..."': '"Waiting..."',
    '"无 (免登录)"': '"None (No login)"',
    '"Chrome 浏览器"': '"Chrome Browser"',
    '"Edge 浏览器"': '"Edge Browser"',
    '"Firefox 浏览器"': '"Firefox Browser"',
    '"Brave 浏览器"': '"Brave Browser"',
    '"通用 (YouTube/Bilibili 等)"': '"Generic (YouTube/Bilibili etc.)"',
    '"剪贴板 (粘贴文本)"': '"Clipboard (Paste text)"',
    '"选择 cookies.txt 文件..."': '"Select cookies.txt..."',
    '"Text Files"': '"Text Files"',
    '"All Files"': '"All Files"',
    '"开始下载"': '"Start Download"',
    '"⏸ 暂停"': '"⏸ Pause"',
    '"▶继续"': '"▶ Resume"',
    '"⏹ 停止"': '"⏹ Stop"'
}

for k, v in substitutions.items():
    text = text.replace(k, v)

with open("videodownloader/gui/app.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Applied clean translations.")
