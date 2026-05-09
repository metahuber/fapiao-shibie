@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  打 包 脚 本
echo ========================================
echo.

:: 读取版本号（GBK 编码兼容）
python -c "exec(open('InvoiceApp/__init__.py',encoding='utf-8').read()); print(__version__)" > _ver.tmp
set /p VERSION=<_ver.tmp
del _ver.tmp
echo 版本：%VERSION%

:: 1. PyInstaller 打包
echo.
echo [1/3] 正在打包，请稍候...
python -m PyInstaller InvoiceApp.spec
if %errorlevel% neq 0 (
    echo 打包失败！
    pause
    exit /b 1
)
echo OK

:: 2. 制作安装包（用 PowerShell 传参，兼容 Inno Setup 6.7+）
echo.
echo [2/3] 制作安装包...
set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\iscc.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\iscc.exe"
) else if exist "C:\Program Files\Inno Setup 6\iscc.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\iscc.exe"
) else (
    set ISCC=iscc
)
:: 生成带版本号的临时 iss 文件并编译
python build_iss.py %VERSION%
"%ISCC%" _installer.iss
del _installer.iss _installer.iss.bak 2>nul
if %errorlevel% neq 0 (
    echo 安装包制作失败！
    pause
    exit /b 1
)
echo OK

:: 3. 完成
echo.
echo ========================================
echo 安装包已生成：
echo dist\数电发票识别工具_Setup_v%VERSION%.exe
echo ========================================
pause
