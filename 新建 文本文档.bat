@echo off
:: 设置控制台编码为 UTF-8，支持中文显示
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 设定版本记录文件路径
set VERSION_FILE=version.txt
set DEFAULT_VERSION=0.1.1

:: 检查版本记录文件是否存在
if not exist "%VERSION_FILE%" (
    echo %DEFAULT_VERSION%> "%VERSION_FILE%"
    echo [提示] 已初始化版本号文件为 %DEFAULT_VERSION%
)

:: 读取当前版本号
set /p CURRENT_VERSION=<"%VERSION_FILE%"

:: 解析版本号 (格式: Major.Minor.Patch)
for /f "tokens=1,2,3 delims=." %%a in ("%CURRENT_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
    set PATCH=%%c
)

:: 将修订号 (Patch) 加 1
set /a NEW_PATCH=!PATCH! + 1
set NEW_VERSION=!MAJOR!.!MINOR!.!NEW_PATCH!

:: 将更新后的版本号写回文件
echo %NEW_VERSION%> "%VERSION_FILE%"

set TAG_NAME=v%NEW_VERSION%

echo ===================================================
echo   上一次版本号: v%CURRENT_VERSION%
echo   即将发布新版本: %TAG_NAME%
echo ===================================================

:: 输入提交备注
set /p COMMIT_MSG="请输入本次发布的提交备注 (直接按回车使用默认备注): "
if "%COMMIT_MSG%"=="" set COMMIT_MSG=Auto release %TAG_NAME%

echo.
echo [1/5] 正在添加文件到暂存区...
git add .

echo [2/5] 正在提交更改...
git commit -m "%COMMIT_MSG%"

echo [3/5] 正在创建 Git 标签 %TAG_NAME%...
git tag %TAG_NAME%

:: ---------------------------------------------------
:: 核心重试逻辑：推送主分支
:: ---------------------------------------------------
:PUSH_MAIN
echo [4/5] 正在推送主分支代码到 GitHub...
git push origin main
if errorlevel 1 (
    goto NETWORK_ERROR
)

:: ---------------------------------------------------
:: 核心重试逻辑：推送标签
:: ---------------------------------------------------
:PUSH_TAG
echo [5/5] 正在推送标签 %TAG_NAME% 到 GitHub...
git push origin %TAG_NAME%
if errorlevel 1 (
    goto NETWORK_ERROR
)

:: 如果全部成功，跳到成功提示
goto SUCCESS

:: ---------------------------------------------------
:: 网络错误处理与重试菜单
:: ---------------------------------------------------
:NETWORK_ERROR
echo.
echo ===================================================
echo   [警告] 哎呀，网络连接失败或推送超时！
echo   请检查你的代理软件（如 Clash）是否已经开启。
echo ===================================================
echo 请选择后续操作：
echo   [1] 已经打开代理，重试推送
echo   [2] 放弃本次推送并退出脚本
echo ===================================================
set /p CHOICE="请输入选项数字 (1 或 2): "

if "%CHOICE%"=="1" (
    echo.
    echo [重试] 正在重新尝试连接并推送...
    goto PUSH_MAIN
) else (
    echo.
    echo [提示] 已退出。下次网络恢复时，只需在终端手动执行：
    echo   git push origin main
    echo   git push origin %TAG_NAME%
    goto END
)

:SUCCESS
echo.
echo ===================================================
echo   发布成功！新版本号: %TAG_NAME%
echo ===================================================

:END
echo.
pause