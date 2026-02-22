import os
import sys
import subprocess
import argparse
import PyInstaller.__main__
from pathlib import Path
import customtkinter

def build():
    parser = argparse.ArgumentParser(description="Build VideoDownloader GUI executable")
    parser.add_argument("--with-node", action="store_true", help="Bundle Node.js executable with the application")
    args = parser.parse_args()

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
    ]
    # 关键: 把 CTk 的 json / 字体资源打包进程序
    pyinstaller_args.append(f'--add-data={customtkinter_path}:customtkinter')

    # 检测并打包 Node.js（如果提供并且启用了参数）
    node_exe_path = project_root / ("node.exe" if os.name == 'nt' else "node")
    if node_exe_path.exists():
        if args.with_node:
            pyinstaller_args.append(f'--add-binary={node_exe_path};.')
            print(f"➡️ 发现自带的 Node.js ({node_exe_path.name}) 且已开启 --with-node，已将其加入打包配置中...")
        else:
            print(f"💡 提示: 在项目根目录检测到了 Node.js ({node_exe_path.name})。")
            print("         如需将其一并打包进独立程序中 (解决一些平台的签名校验问题)，")
            print("         请在打包时添加参数： python build_exe.py --with-node")
            print("         (当前采用默认行为：未打包 Node.js 以控制包体积)")

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
