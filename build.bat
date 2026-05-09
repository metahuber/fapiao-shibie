@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  数电发票识别工具 — 打包脚本
echo ========================================
echo.

:: 读取版本号
for /f "tokens=2 delims== " %%a in ('type InvoiceApp\__init__.py ^| findstr __version__') do set "VERSION=%%a"
set "VERSION=%VERSION:'=%"
set "VERSION=%VERSION: =%"
echo 当前版本：%VERSION%

:: 1. PyInstaller 打包
echo.
echo [1/3] PyInstaller 打包中...
py -m PyInstaller InvoiceApp.spec
if errorlevel 1 (
    echo 打包失败，请检查错误信息
    pause
    exit /b 1
)
echo [OK]

:: 2. 制作 Inno Setup 安装包
echo.
echo [2/3] 制作安装包中...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" -Version "%VERSION%"
if errorlevel 1 (
    echo.
    echo 安装包制作失败！
    echo 请确认已安装 Inno Setup：https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)
echo [OK]

:: 3. 完成
echo.
echo [3/3] 打包完成！
echo.
echo 安装包位置：
echo dist\数电发票识别工具_Setup_v%VERSION%.exe
echo.

:: 打开输出目录
explorer dist

pause
