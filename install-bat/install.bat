@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem 检查 Python 版本
for /f "tokens=2 delims=." %%a in ('python --version 2^>^&1') do (
    set "major=%%a"
    for /f "tokens=1 delims= " %%b in ("%%a") do (
        set "minor=%%b"
    )
)

echo DG-LAB_Punisher 安装器 V0.1

if "%major%" == "3" if "%minor%" == "7" (
    echo 当前 Python 版本是 3.7，继续执行后续操作。
) else (
    echo 当前 Python 版本不是 3.7，开始下载 Python 3.7。
    powershell -Command "(New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.7.9/python-3.7.9-amd64.exe', 'python-3.7.9-amd64.exe')"
    echo 下载完成，开始安装 Python 3.7。
    start /wait python-3.7.9-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del python-3.7.9-amd64.exe
    echo Python 3.7 安装完成。
)

rem 创建虚拟环境
echo 创建虚拟环境...
python -m venv myenv

rem 激活虚拟环境
call myenv\Scripts\activate.bat

rem 安装依赖库（假设依赖库在 requirements.txt 中）
if exist requirements.txt (
    echo 开始安装依赖库...
    pip install -r requirements.txt
    echo 依赖库安装完成。
) else (
    echo 未找到 requirements.txt 文件，请检查文件
)

rem 停用虚拟环境
deactivate

echo 所有操作完成。
endlocal

pause