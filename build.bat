@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  数电发票识别工具 — 打包脚本
echo ========================================
echo.

:: 第 0 步：查找 Python（支持 py / python3 / python）
set PYTHON=python
where /q py 2>nul && set PYTHON=py
where /q python3 2>nul && if "%PYTHON%"=="python" set PYTHON=python3

:: 确认 Python 可用
%PYTHON% --version >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Python，请确认已安装 Python 3.10+
    pause
    exit /b 1
)

:: 读取版本号
%PYTHON% -c "exec(open('InvoiceApp/__init__.py').read()); print(__version__)" > _version.tmp
set /p VERSION=<_version.tmp
del _version.tmp
echo 当前版本：%VERSION%

:: 1. PyInstaller 打包
echo.
echo [1/3] PyInstaller 打包中...
%PYTHON% -m PyInstaller InvoiceApp.spec
if errorlevel 1 (
    echo 打包失败，请检查错误信息
    pause
    exit /b 1
)
echo [OK]

:: 2. 制作 Inno Setup 安装包
echo.
echo [2/3] 制作安装包中...

:: 查找 iscc.exe
set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\iscc.exe" set ISCC=C:\Program Files (x86)\Inno Setup 6\iscc.exe
if exist "C:\Program Files\Inno Setup 6\iscc.exe" set ISCC=C:\Program Files\Inno Setup 6\iscc.exe
if "%ISCC%"=="" set ISCC=iscc

:: 用 PowerShell 调用（处理路径空格）
powershell -NoProfile -Command "& '%ISCC%' installer.iss /Q /DMyAppVersion=%VERSION%"
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
if exist dist\nul (
    explorer dist
) else (
    echo [提示] dist 目录不存在，可能打包未成功
)

pause
