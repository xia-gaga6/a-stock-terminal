"""
A股金融终端 — EXE 打包脚本
使用 PyInstaller 将 Flask 后端 + 前端页面打包为单文件 EXE
"""
import PyInstaller.__main__
import os

HERE = os.path.abspath(os.path.dirname(__file__))

PyInstaller.__main__.run([
    os.path.join(HERE, 'server.py'),
    '--name=AStockTerminal',
    '--onefile',
    '--noconsole',
    '--add-data=' + os.path.join(HERE, 'index.html') + ';.',
    '--add-data=' + os.path.join(HERE, 'README.md') + ';.',
    '--collect-all=flask',
    '--collect-all=flask_cors',
    '--collect-all=requests',
    '--collect-all=jinja2',
    '--collect-all=werkzeug',
    '--collect-all=markupsafe',
    '--collect-all=click',
    '--collect-all=blinker',
    '--collect-all=itsdangerous',
    '--distpath=' + os.path.join(HERE, 'dist'),
    '--workpath=' + os.path.join(HERE, 'build'),
    '--specpath=' + HERE,
    '--clean',
])

print("\n" + "=" * 50)
print("Build complete! EXE: dist/AStockTerminal.exe")
print("=" * 50)
