@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  发布到 GitHub Releases
echo ========================================
echo.

:: 检查 gh 是否安装
gh --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 GitHub CLI
    echo.
    echo 请运行以下命令安装：
    echo   winget install GitHub.cli
    echo.
    echo 安装后执行 gh auth login 登录 GitHub
    pause
    exit /b 1
)

:: 读取版本号
python -c "exec(open('InvoiceApp/__init__.py').read()); print(__version__)" > _ver.tmp
set /p VER=<_ver.tmp
del _ver.tmp
echo 版本：%VER%
echo.

:: 检查是否已打包
set INSTALLER=dist\数电发票识别工具_Setup_v%VER%.exe
if not exist "%INSTALLER%" (
    echo [提示] 未找到安装包，先执行打包...
    call build.bat
    if %errorlevel% neq 0 (
        echo 打包失败，发布中止
        pause
        exit /b 1
    )
)

:: 确认发布
echo.
echo 即将发布 v%VER% 到 GitHub，包含：
echo   %INSTALLER%
echo.
set /p CONFIRM=确认发布？(y/n):
if /i not "%CONFIRM%"=="y" (
    echo 已取消
    pause
    exit /b 1
)

:: 创建标签并推送
echo.
echo [1/3] 推送标签...
git tag v%VER%
if %errorlevel% neq 0 (
    echo 标签 v%VER% 已存在，跳过
)
git push origin v%VER%
echo OK

:: 创建 Release
echo.
echo [2/3] 创建 Release...
gh release create v%VER% --title "v%VER%" --notes ""
echo OK

:: 上传安装包
echo.
echo [3/3] 上传安装包...
gh release upload v%VER% "%INSTALLER%" --clobber
echo OK

:: 完成
echo.
echo ========================================
echo  发布完成！
echo  https://github.com/metahuber/fapiao-shibie/releases/tag/v%VER%
echo ========================================
pause
