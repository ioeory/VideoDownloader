import re
import pprint

with open("videodownloader/gui/app.py", "r", encoding="utf-8") as f:
    text = f.read()

# Make sure we don't translate dict keys in the injection itself
dict_part, rest = text.split("self.i18n = {", 1)
i18n_end_idx = rest.find("        }") + 9
i18n_decl = rest[:i18n_end_idx]
rest = rest[i18n_end_idx:]

matches = set(re.findall(r"([\"'])(.*?[\u4e00-\u9fa5].*?)\1", rest))
strings = [m[1] for m in matches]
print("Found untranslated Chinese strings:", len(strings))

translations = {
    "🌐 EN / 中文": "🌐 EN / 中文",
    "VideoDownloader - 通用视频下载器": "VideoDownloader - 通用视频下载器",
    "视频/课程 URL:": "视频/课程 URL:",
    "下载平台:": "下载平台:",
    "最高画质:": "最高画质:",
    "输出目录:": "输出目录:",
    "浏览...": "浏览...",
    "Cookies 来源:": "Cookies 来源:",
    "日志级别:": "日志级别:",
    "并发线程:": "并发线程:",
    "等待下载...": "等待下载...",
    "开始下载": "开始下载",
    "⏸ 暂停": "⏸ 暂停",
    "▶ 继续": "▶ 继续",
    "⏹ 停止": "⏹ 停止",
    "播放列表范围:": "播放列表范围:",
    "如 1-25 或 1,3,5 (留空下载所有)": "如 1-25 或 1,3,5 (留空下载所有)",
    "下载字幕": "下载字幕",
    "说明: Harvard 模式支持自动探测播放列表。将全自动提取指定页面或\\n播放列表下的所有 YouTube 视频、MP4 直链、PDF 讲义与源码包素材。": "说明: Harvard 模式支持自动探测播放列表。... ",
    "指定 Week(s):": "指定 Week(s):",
    "如: 1 2 (空格分隔, 留空下载全部)": "如: 1 2 (空格分隔, 留空下载全部)",
    "欢迎使用 VideoDownloader GUI 版本！由于部分环境缺少配置，在启动期间如有卡顿属于正常现象。": "欢迎使用 VideoDownloader GUI 版本！",
    "🌐 中文 / EN": "🌐 中文 / EN",
    
    # Add new translations
    "此操作不支持该系统。": "This operation is not supported on this OS.",
    "确  认": "Confirm",
    "取消": "Cancel",
    "确认": "Confirmation",
    "确定要停止当前下载(会取消后续任务)吗？": "Are you sure you want to stop the current download? (Queued tasks will be cancelled)",
    "正在强制停止，请稍候...": "Force stopping, please wait...",
    "已暂停: ": "Paused: ",
    "   |   速度: ": "   |   Speed: ",
    "并发下载中 (多线程活动)... 请查看左侧日志": "Concurrent downloading... Check logs",
    "，正在合并或处理...": ", processing...",
    "警告": "Warning",
    "请输入 URL 或 Course Slug": "Please enter URL or Course Slug",
    "启动期间如有卡顿属于正常现象。": "Stuttering during startup is normal.",
    "未找到需要下载的课时内容": "No downloadable content found",
    "没有解析出任何下载任务。": "No download tasks could be parsed.",
    " 个下载子任务，准备下载...": " sub-tasks, preparing download...",
    "🚫 队列执行已中止": "🚫 Queue execution aborted",
    "解析真实文件名中...": "Resolving actual filename...",
    "\n---> 开始执行任务 [": "\n---> Starting task [",
    "即将开始: ": "Starting soon: ",
    " (包含失败项)": " (Includes failed items)",
    "🚫 任务已终止: ": "🚫 Task terminated: ",
    "执行期间异常: ": " exception during execution: ",
    " (异常)": " (Exception)",
    "⚠️ 部分/瑕疵: ": "⚠️ Partial: ",
    "🚫 子任务已终止: ": "🚫 Sub-task terminated: ",
    "🛑 下载已被用户提前手动停止。完成情况: ": "🛑 Download manually stopped. Completions: ",
    " 成功。": " successful.",
    "✅ 队列执行完毕！成功 ": "✅ Queue execution finished! Success: ",
    "，部分/瑕疵 ": ", Partial: ",
    "，完全失败 ": ", completely failed: ",
    "⚠️ 以下任务未能完整下载，请检查其页面状态：": "⚠️ The following tasks failed to download completely:",
    "有任务未能成功下载": "Some tasks failed to download",
    "在刚才的批量队列中，有 ": "In the previous batch queue, ",
    " 个任务无法完整下载：\n\n": " tasks failed to finish:\n\n",
    "\n\n详情请查看左侧日志区域。": "\n\nCheck logs for details.",
    "❌ 下载过程发生未知错误: ": "❌ Unknown error occurred: ",
    "已手动打断。已完成 ": "Manually interrupted. Completed ",
    " 个任务。": " tasks.",
    "程序抛出严重异常，请检查上方日志。": "Execution exception, check logs.",
    "下载成功！(点击再次发车)": "✅ All Completed (Click to restart)",
    "全部任务完美处理完毕！": "All tasks have been processed!",
    "包含失败项 (提示在上方)": "Contains failed tasks (Check logs)",
    "成 {success_count} 瑕 {partial_count} 败 {len(tasks) - success_count - partial_count}。": "Success: {success_count}, Partial: {partial_count}, Failed: {len(tasks) - success_count - partial_count}.",
    "全军覆没 (点击重传)": "All failed (Click to retry)",
    "所有下载任务均已失败。": "All tasks failed.",
    "正在尝试获取 Cookie (": "Trying to get Cookie (",
    ")...": ")...",
    "使用手动提供的 Cookie (": "Using manual Cookie (",
    " 个)": " items)",
    "成功获取到 ": "Successfully got ",
    " 条 Cookie 记录。": " Cookie records.",
    "获取 Cookie 失败: ": "Failed to get Cookie: "
}

new_en = {}
new_zh = {}
key_counter = 1

for s in strings:
    # Check if this string is somehow a substring or exactly matches 
    if s in translations:
        key = f"dyn_{key_counter}"
        key_counter += 1
        new_en[key] = translations[s]
        new_zh[key] = s
        
        # Replace in text: wrap with self.t(key)
        # Note: we must identify if it's f-string or normal string
        rest = rest.replace(f'"{s}"', f'self.t("{key}")')
        rest = rest.replace(f"'{s}'", f'self.t("{key}")')
    else:
        # F-string cases (e.g., f"已暂停: {Path...}")
        # we can't simple wrap self.t() around an f-string inside.
        print("Skipping dynamic F-String or untranslated string:", s)

# Also handle those f-string parts that are hardcoded. We need regex to replace them cautiously.
pattern_subs = {
    f'f"已下载完成: {{filename}}，正在合并或处理..."': f'f"{{self.t(\'finished\')}}: {{filename}}{{self.t(\'processing\')}}"',
    f'f"已暂停: {{Path(d.get(\'filename\', \'\')).name}}"': f'f"{{self.t(\'paused\')}}{{Path(d.get(\'filename\', \'\')).name}}"',
    f'f"正在下载: {{filename}}   |   速度: {{speed}}"': f'f"{{self.t(\'downloading\')}}{{filename}} {{self.t(\'speed\')}}{{speed}}"',
    f'f"即将开始: {{name}}"': f'f"{{self.t(\'starting_soon\')}}{{name}}"',
    f'f"🚫 任务已终止: {{display_name}}"': f'f"{{self.t(\'task_terminated\')}}{{display_name}}"',
    f'f"❌ 任务 {{display_name}} 执行期间异常: {{task_err}}"': f'f"{{self.t(\'task_exception\')}} {{display_name}}: {{task_err}}"',
    f'f"[{i}/{total_tasks}] ⚠️ 部分/瑕疵: {{name}}"': f'f"[{{i}}/{{total_tasks}}] {{self.t(\'partial\')}}{{name}}"',
    f'f"[{i}/{total_tasks}] ❌ 异常 ({{display_name}}): {{task_err}}"': f'f"[{{i}}/{{total_tasks}}] {{self.t(\'exception\')}} ({{display_name}}): {{task_err}}"',
    f'f"🚫 子任务已终止: {{display_name}}"': f'f"{{self.t(\'sub_task_terminated\')}}{{display_name}}"',
    f'f"🛑 下载已被用户提前手动停止。完成情况: {{success_count}} 成功。"': f'f"{{self.t(\'stopped_summary_1\')}} {{success_count}} {{self.t(\'stopped_summary_2\')}}"',
    f'f"✅ 队列执行完毕！成功 {{success_count}}，部分/瑕疵 {{partial_count}}，完全失败 {{len(tasks) - success_count - partial_count}}。"': f'f"{{self.t(\'queue_finished_1\')}}{{success_count}}{{self.t(\'queue_finished_2\')}}{{partial_count}}{{self.t(\'queue_finished_3\')}}{{len(tasks) - success_count - partial_count}}."',
    f'f"在刚才的批量队列中，有 {{len(error_msg_lines)}} 个任务无法完整下载：\\n\\n{{display_text}}\\n\\n详情请查看左侧日志区域。"': f'f"{{self.t(\'batch_failed_1\')}} {{len(error_msg_lines)}} {{self.t(\'batch_failed_2\')}}\\n\\n{{display_text}}\\n\\n{{self.t(\'batch_failed_3\')}}"',
    f'f"❌ 下载过程发生未知错误: {{e}}"': f'f"{{self.t(\'unknown_error\')}}{{e}}"',
    f'f"已手动打断。已完成 {{success_count}} 个任务。"': f'f"{{self.t(\'interrupted_1\')}}{{success_count}}{{self.t(\'interrupted_2\')}}"',
    f'f"成 {{success_count}} 瑕 {{partial_count}} 败 {{len(tasks) - success_count - partial_count}}。"': f'f"{{self.t(\'stats_success\')}} {{success_count}} {{self.t(\'stats_partial\')}} {{partial_count}} {{self.t(\'stats_failed\')}} {{len(tasks) - success_count - partial_count}}."',
    f'f"正在尝试获取 Cookie ({{cookie_src}})..."': f'f"{{self.t(\'trying_cookie_1\')}}{{cookie_src}}{{self.t(\'trying_cookie_2\')}}"',
    f'f"使用手动提供的 Cookie ({{len(parsed_cookies)}} 个)"': f'f"{{self.t(\'manual_cookie\')}}{{len(parsed_cookies)}}{{self.t(\'cookie_items\')}}"',
    f'f"成功获取到 {{len(parsed_cookies)}} 条 Cookie 记录。"': f'f"{{self.t(\'got_cookies_1\')}}{{len(parsed_cookies)}}{{self.t(\'got_cookies_2\')}}"',
    f'f"获取 Cookie 失败: {{e}}"': f'f"{{self.t(\'failed_cookie_1\')}}{{e}}"',
    f'f"发现 {{total_tasks}} 个下载子任务，准备下载..."': f'f"{{self.t(\'found_tasks_1\')}}{{total_tasks}}{{self.t(\'found_tasks_2\')}}"',
    f'f"\\n---> 开始执行任务 [{{i+1}}/{{total_tasks}}]: {{display_name}}"': f'f"\\n---> {{self.t(\'start_task\')}} [{{i+1}}/{{total_tasks}}]: {{display_name}}"'
}

new_en.update({
    "finished": "Finished: ",
    "processing": ", processing...",
    "paused": "Paused: ",
    "downloading": "Downloading: ",
    "speed": " | Speed: ",
    "starting_soon": "Starting soon: ",
    "task_terminated": "🚫 Task terminated: ",
    "task_exception": "❌ Task",
    "partial": "⚠️ Partial: ",
    "exception": "❌ Exception",
    "sub_task_terminated": "🚫 Sub-task terminated: ",
    "stopped_summary_1": "🛑 Download stopped manually. ",
    "stopped_summary_2": "successful.",
    "queue_finished_1": "✅ Queue execution finished! Success: ",
    "queue_finished_2": ", Partial: ",
    "queue_finished_3": ", Completely Failed: ",
    "batch_failed_1": "In the recent batch queue, ",
    "batch_failed_2": " tasks could not be downloaded completely:",
    "batch_failed_3": "Check logs for details.",
    "unknown_error": "❌ Unknown error occurred: ",
    "interrupted_1": "Manually interrupted. Completed ",
    "interrupted_2": " tasks.",
    "stats_success": "Success:",
    "stats_partial": "Partial:",
    "stats_failed": "Failed:",
    "trying_cookie_1": "Trying to get Cookie from (",
    "trying_cookie_2": ")...",
    "manual_cookie": "Using manual Cookie (",
    "cookie_items": " items)",
    "got_cookies_1": "Successfully extracted ",
    "got_cookies_2": " Cookie items.",
    "failed_cookie_1": "Failed to get Cookie: ",
    "found_tasks_1": "Found ",
    "found_tasks_2": " sub-tasks, preparing download...",
    "start_task": "Starting task"
})

new_zh.update({
    "finished": "已下载完成: ",
    "processing": "，正在合并或处理...",
    "paused": "已暂停: ",
    "downloading": "正在下载: ",
    "speed": "   |   速度: ",
    "starting_soon": "即将开始: ",
    "task_terminated": "🚫 任务已终止: ",
    "task_exception": "❌ 任务",
    "partial": "⚠️ 部分/瑕疵: ",
    "exception": "❌ 异常",
    "sub_task_terminated": "🚫 子任务已终止: ",
    "stopped_summary_1": "🛑 下载已被用户提前手动停止。完成情况: ",
    "stopped_summary_2": "成功。",
    "queue_finished_1": "✅ 队列执行完毕！成功 ",
    "queue_finished_2": "，部分/瑕疵 ",
    "queue_finished_3": "，完全失败 ",
    "batch_failed_1": "在刚才的批量队列中，有 ",
    "batch_failed_2": " 个任务无法完整下载：",
    "batch_failed_3": "详情请查看左侧日志区域。",
    "unknown_error": "❌ 下载过程发生未知错误: ",
    "interrupted_1": "已手动打断。已完成 ",
    "interrupted_2": " 个任务。",
    "stats_success": "成",
    "stats_partial": "瑕",
    "stats_failed": "败",
    "trying_cookie_1": "正在尝试获取 Cookie (",
    "trying_cookie_2": ")...",
    "manual_cookie": "使用手动提供的 Cookie (",
    "cookie_items": " 个)",
    "got_cookies_1": "成功获取到 ",
    "got_cookies_2": " 条 Cookie 记录。",
    "failed_cookie_1": "获取 Cookie 失败: ",
    "found_tasks_1": "发现 ",
    "found_tasks_2": " 个下载子任务，准备下载...",
    "start_task": "开始执行任务"
})

for k, v in pattern_subs.items():
    if k in rest:
        rest = rest.replace(k, v)

# Reconstruct i18n
import json
i18n_code = (
    "        self.i18n['en'].update(" + json.dumps(new_en, indent=12) + ")\n"
    "        self.i18n['zh'].update(" + json.dumps(new_zh, indent=12) + ")\n\n"
)

# Find where to inject
inject_idx = rest.find("        self.update_ui_texts()")
if inject_idx != -1:
    rest = rest[:inject_idx] + i18n_code + rest[inject_idx:]
else:
    print("Cannot find update_ui_texts to inject new i18n!")

# Save back
final_text = dict_part + "self.i18n = {" + i18n_decl + rest
with open("videodownloader/gui/app.py", "w", encoding="utf-8") as f:
    f.write(final_text)

print("Translation strings successfully refactored and injected in app.py!")

