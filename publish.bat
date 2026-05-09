@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  发布到 GitHub Releases
echo ========================================
echo.

gh --version >nul 2>nul || (
    echo 请先安装 GitHub CLI：winget install GitHub.cli
    pause & exit /b 1
)

:: 版本号
python -c "exec(open('InvoiceApp/__init__.py').read()); print(__version__)" > _ver.tmp
set /p VER=<_ver.tmp
del _ver.tmp
echo 版本：%VER%

:: 检查安装包
set INSTALLER=dist\数电发票识别工具_Setup_v%VER%.exe
if not exist "%INSTALLER%" (
    echo [运行 build.bat 打包中...]
    call build.bat
)
if not exist "%INSTALLER%" (
    echo 安装包未找到：%INSTALLER%
    pause & exit /b 1
)

:: 确认
echo 即将发布：%INSTALLER%
set /p OK=确认？(y/n):
if /i not "%OK%"=="y" echo 已取消 & pause & exit /b 1

:: 推送标签
echo.
git tag v%VER% 2>nul
git push origin v%VER%
echo [标签已推送]

:: 一步创建 Release + 上传安装包
echo 发布中...
gh release create v%VER% "%INSTALLER%" --title "v%VER%" --notes "" 2>nul
if errorlevel 1 (
    :: 可能已存在，尝试上传
    gh release upload v%VER% "%INSTALLER%" --clobber
)

echo.
echo 完成！
echo https://github.com/metahuber/fapiao-shibie/releases/tag/v%VER%
pause
