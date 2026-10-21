@echo off
chcp 65001 >nul
setlocal

rem ============================================================
rem   修复 MPE「原生 OCR」识别失败
rem
rem   原因：LocalBridge 的工作目录是 MPE Desktop 的安装目录，
rem         它按相对路径 ./model/ocr 找自带 OCR 模型，
rem         但那里没有这个目录 -> 模型加载 0 毫秒失败。
rem   做法：在安装目录建一个 model 目录链接，指向项目的模型目录。
rem
rem   MPE 升级 / 重装后这个链接会丢，重新跑一次本脚本即可。
rem ============================================================

set "LINK=D:\MAA\MPE Desktop\model"
set "SRC=D:\MAA\MAA-HazeWorld\assets\resource\model"

if not exist "%SRC%\ocr\det.onnx" (
    echo [错误] 找不到模型文件: %SRC%\ocr\det.onnx
    echo        请确认项目路径没变。
    pause
    exit /b 1
)

if not exist "D:\MAA\MPE Desktop" (
    echo [错误] 找不到 MPE 安装目录: D:\MAA\MPE Desktop
    pause
    exit /b 1
)

if exist "%LINK%" (
    echo [信息] 链接已存在，无需处理:
    echo        %LINK%  ==^>  %SRC%
    pause
    exit /b 0
)

echo 正在创建目录链接...
mklink /J "%LINK%" "%SRC%"
if errorlevel 1 (
    echo [错误] 创建失败。如果是权限问题，右键“以管理员身份运行”。
    pause
    exit /b 1
)

echo.
echo [完成] 已链接: %LINK%  ==^>  %SRC%
echo        重启 MPE 后原生 OCR 即可使用。
pause
