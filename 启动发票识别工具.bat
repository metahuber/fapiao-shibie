@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -X utf8 "%~dp0发票识别工具.py"
pause
