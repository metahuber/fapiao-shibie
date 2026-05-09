@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  打 包 脚 本
echo ========================================
echo.

:: 读取版本号
python -c "exec(open('InvoiceApp/__init__.py').read()); print(__version__)" > _ver.tmp
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

:: 2. 制作安装包
echo.
echo [2/3] 制作安装包...
if exist "C:\Program Files (x86)\Inno Setup 6\iscc.exe" (
    "C:\Program Files (x86)\Inno Setup 6\iscc.exe" installer.iss /Q /DMyAppVersion=%VERSION%
) else (
    if exist "C:\Program Files\Inno Setup 6\iscc.exe" (
        "C:\Program Files\Inno Setup 6\iscc.exe" installer.iss /Q /DMyAppVersion=%VERSION%
    ) else (
        iscc installer.iss /Q /DMyAppVersion=%VERSION%
    )
)
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
echo dist\Setup_v%VERSION%.exe
echo ========================================
pause
