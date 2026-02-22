import os
import sys
import subprocess
import PyInstaller.__main__
from pathlib import Path
import customtkinter

def build():
    # 查找 customtkinter 库的安装路径，以便打包皮肤和字体资源
    customtkinter_path = os.path.dirname(customtkinter.__file__)

    # VideoDownloader 根目录
    project_root = Path(__file__).parent.absolute()
    app_entry = project_root / "videodownloader" / "gui" / "app.py"

    if not app_entry.exists():
        print(f"Error: 找不到 GUI 入口文件在 {app_entry}")
        sys.exit(1)

    # 准备 PyInstaller 的参数
    pyinstaller_args = [
        str(app_entry),  # 目标脚本
        '--name=VideoDownloader', # 输出文件名
        '--noconsole',   # 隐藏命令行黑框 (非 Console 模式)
        '--onefile',     # 打包成单个独立可执行文件（消除 _internal 文件夹）
        '--clean',       # 每次构建清空缓存
        '--noconfirm',   # 覆盖已有构建不确认
        '--log-level=INFO',
        f'--add-data={customtkinter_path}:customtkinter', # 关键: 把 CTk 的 json / 字体资源打包进程序
    ]

    # 为了更好的兼容性，特别是 Linux 打包给 Linux (由于我们是在 WSL 下开发，实际打包的出的是 ELF 二进制，如果要在 Windows 运行需在 Windows 下打包)
    print("=" * 60)
    print("🚀 开始使用 PyInstaller 构建 GUI 独立程序...")
    print(f"命令参数: pyinstaller {' '.join(pyinstaller_args)}")
    print("=" * 60)

    try:
        PyInstaller.__main__.run(pyinstaller_args)
        print("=" * 60)
        print("✅ 构建完成! 结果已存放在当前目录下的 `dist/` 文件夹中。")
        print("您现在可以直接将独立的 VideoDownloader 可执行文件发给别人使用了！")
    except Exception as e:
        print(f"❌ 构建过程中发生错误: {e}")

if __name__ == "__main__":
    build()
