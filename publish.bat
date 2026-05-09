@echo off
chcp 65001 >nul
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo ========================================
echo  一键打包（PyInstaller + Inno Setup）
echo ========================================
echo.

:: 版本号
python -c "exec(open('InvoiceApp/__init__.py').read()); print(__version__)" > _ver.tmp
set /p VER=<_ver.tmp
del _ver.tmp
echo 版本：%VER%

:: 检查安装包是否已存在
set INSTALLER=dist\数电发票识别工具_Setup_v%VER%.exe
if exist "%INSTALLER%" (
    echo 安装包已存在：%INSTALLER%
    set /p REBUILD=重新打包？(y/n):
    if /i not "!REBUILD!"=="y" echo 跳过打包 & goto :done
)

echo [运行 build.bat 打包中...]
call build.bat

:done
echo.
echo ========================================
echo 安装包路径：%INSTALLER%
echo 手动发布到 GitHub Releases：
echo   1. 打开 https://github.com/metahuber/fapiao-shibie/releases
echo   2. 点击 "Create a new release"
echo   3. 上传 %INSTALLER%
echo ========================================
pause
