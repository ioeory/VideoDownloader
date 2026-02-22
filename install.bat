@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: ============================================================
:: VideoDownloader — Windows 一键安装脚本
:: ============================================================
:: 功能：
::   1. 检测并安装 Python 3.10+
::   2. 安装 videodownloader 包及所有依赖
::   3. 下载 ffmpeg 并配置 PATH
::   4. 下载 Node.js (可选, 解决 YouTube Cookie 签名问题)
::
:: 使用方法：
::   右键以管理员身份运行，或直接双击执行
:: ============================================================

title VideoDownloader Installer
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║     VideoDownloader — Windows 一键安装       ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: ─────────────────────────────────────────────
:: 配置
:: ─────────────────────────────────────────────
set "INSTALL_DIR=%LOCALAPPDATA%\VideoDownloader"
set "FFMPEG_DIR=%INSTALL_DIR%\ffmpeg"
set "PYTHON_VERSION=3.12.8"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-amd64.exe"
set "FFMPEG_URL=https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
set "FFMPEG_ZIP=%TEMP%\ffmpeg.zip"

:: 创建安装目录
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: ─────────────────────────────────────────────
:: Step 1: 检测 Python
:: ─────────────────────────────────────────────
echo [1/4] 检测 Python 环境...

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
    echo       已安装 Python !PY_VER!

    :: 检查版本是否 >= 3.10
    for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
        set "PY_MAJOR=%%a"
        set "PY_MINOR=%%b"
    )
    if !PY_MAJOR! geq 3 if !PY_MINOR! geq 10 (
        echo       ✅ Python 版本满足要求 ^(^>=3.10^)
        goto :python_ok
    )
    echo       ⚠️  Python 版本过低，需要 3.10+，将安装新版本...
) else (
    echo       未检测到 Python，将自动安装...
)

:: 下载并安装 Python
echo.
echo       正在下载 Python %PYTHON_VERSION%，请稍候...
echo       URL: %PYTHON_URL%
curl -L -o "%TEMP%\python-installer.exe" "%PYTHON_URL%"
if %ERRORLEVEL% neq 0 (
    echo       ❌ 下载 Python 失败！请检查网络连接或手动下载安装。
    echo       下载地址: %PYTHON_URL%
    pause
    exit /b 1
)

echo       正在安装 Python（静默模式）...
"%TEMP%\python-installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1
if %ERRORLEVEL% neq 0 (
    echo       ❌ Python 安装失败！请手动安装后重试。
    pause
    exit /b 1
)
del "%TEMP%\python-installer.exe" 2>nul

:: 刷新 PATH
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
echo       ✅ Python %PYTHON_VERSION% 安装完成

:python_ok
echo.

:: ─────────────────────────────────────────────
:: Step 2: 安装 videodownloader
:: ─────────────────────────────────────────────
echo [2/4] 安装 VideoDownloader 及依赖...

:: 获取脚本所在目录（即项目根目录）
set "SCRIPT_DIR=%~dp0"

:: 先升级 pip
python -m pip install --upgrade pip >nul 2>&1

:: 安装项目
python -m pip install "%SCRIPT_DIR%."
if %ERRORLEVEL% neq 0 (
    echo       ❌ 安装 VideoDownloader 失败！
    echo       请检查错误信息后重试。
    pause
    exit /b 1
)

:: 验证 vd 命令
where vd >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo       ✅ VideoDownloader 安装成功，命令: vd
) else (
    echo       ⚠️  vd 命令未在 PATH 中找到
    echo       请尝试重启终端或将 Python Scripts 目录添加到 PATH
)
echo.

:: ─────────────────────────────────────────────
:: Step 3: 下载 ffmpeg
:: ─────────────────────────────────────────────
echo [3/4] 检测 ffmpeg...

where ffmpeg >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo       ✅ ffmpeg 已安装，跳过
    goto :ffmpeg_ok
)

echo       未检测到 ffmpeg，正在下载...
echo       URL: %FFMPEG_URL%

curl -L -o "%FFMPEG_ZIP%" "%FFMPEG_URL%"
if %ERRORLEVEL% neq 0 (
    echo       ❌ 下载 ffmpeg 失败！
    echo       请手动下载: %FFMPEG_URL%
    echo       解压后将 bin 目录添加到系统 PATH
    goto :ffmpeg_ok
)

echo       正在解压 ffmpeg...
if not exist "%FFMPEG_DIR%" mkdir "%FFMPEG_DIR%"
powershell -Command "Expand-Archive -Force '%FFMPEG_ZIP%' '%FFMPEG_DIR%'"
del "%FFMPEG_ZIP%" 2>nul

:: 找到解压后的 bin 目录
for /d %%d in ("%FFMPEG_DIR%\ffmpeg-*") do (
    set "FFMPEG_BIN=%%d\bin"
)

if exist "!FFMPEG_BIN!\ffmpeg.exe" (
    :: 添加到用户 PATH（永久生效）
    powershell -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';!FFMPEG_BIN!', 'User')"
    set "PATH=!FFMPEG_BIN!;%PATH%"
    echo       ✅ ffmpeg 已安装到: !FFMPEG_BIN!
    echo       已自动添加到用户 PATH（重启终端生效）
) else (
    echo       ⚠️  ffmpeg 解压异常，请手动处理
)

:ffmpeg_ok
echo.

:: ─────────────────────────────────────────────
:: Step 4: 检测 Node.js（可选）
:: ─────────────────────────────────────────────
echo [4/4] 检测 Node.js（可选，用于 Cookie 模式下载）...

where node >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "tokens=1 delims= " %%v in ('node --version 2^>^&1') do echo       ✅ Node.js %%v 已安装
) else (
    echo       ⚠️  未检测到 Node.js
    echo       如需使用 Cookie 模式（下载私有/会员视频），请安装 Node.js:
    echo       https://nodejs.org/
)

:: ─────────────────────────────────────────────
:: 完成
:: ─────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║           ✅ 安装完成！                      ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  使用方法（打开 cmd 或 PowerShell）:
echo.
echo    vd download "https://www.youtube.com/watch?v=xxx"
echo    vd download "https://..." -q 1080p
echo    vd download "https://...&list=..." --playlist-items 1-25
echo    vd harvard --url "https://cs50.harvard.edu/python/"
echo    vd -h
echo.
echo  后续升级 yt-dlp（修复 YouTube 接口变化）:
echo    pip install --upgrade yt-dlp
echo.
echo  升级 VideoDownloader 本身:
echo    pip install --upgrade videodownloader
echo.
pause

:: ----------------------------------------------------------------------
:: Create Desktop Shortcut for GUI
:: ----------------------------------------------------------------------
echo [5/5] 创建桌面快捷方式...
set "VBS_PATH=%TEMP%\CreateShortcut.vbs"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\VideoDownloader.lnk"
set "ICON_PATH=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_PATH%"
echo sLinkFile = "%SHORTCUT_PATH%" >> "%VBS_PATH%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_PATH%"
echo oLink.TargetPath = "vd-gui.exe" >> "%VBS_PATH%"
echo oLink.WorkingDirectory = "%USERPROFILE%\Downloads" >> "%VBS_PATH%"
echo oLink.IconLocation = "%ICON_PATH%, 0" >> "%VBS_PATH%"
echo oLink.Description = "VideoDownloader GUI" >> "%VBS_PATH%"
echo oLink.Save >> "%VBS_PATH%"

cscript /nologo "%VBS_PATH%"
del "%VBS_PATH%" 2>nul
echo        ✅ 已在桌面生成快捷方式 [VideoDownloader]

