@echo off
setlocal enabledelayedexpansion

:: Set version file path
set VERSION_FILE=version.txt
set DEFAULT_VERSION=0.1.6

:: Check if version file exists
if not exist "%VERSION_FILE%" (
    echo %DEFAULT_VERSION%> "%VERSION_FILE%"
    echo [Info] Initialized version file to %DEFAULT_VERSION%
)

:: Read current version
set /p CURRENT_VERSION=<"%VERSION_FILE%"

:: Parse version components
for /f "tokens=1,2,3 delims=." %%a in ("%CURRENT_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
    set PATCH=%%c
)

:: Increment patch version
set /a NEW_PATCH=!PATCH! + 1
set NEW_VERSION=!MAJOR!.!MINOR!.!NEW_PATCH!

:: Save new version back to file
echo %NEW_VERSION%> "%VERSION_FILE%"

set TAG_NAME=v%NEW_VERSION%

echo ===================================================
echo   Previous Version: v%CURRENT_VERSION%
echo   New Release Version: %TAG_NAME%
echo ===================================================

:: Input commit message
set /p COMMIT_MSG="Enter commit message (Press Enter for default): "
if "%COMMIT_MSG%"=="" set COMMIT_MSG=Auto release %TAG_NAME%

echo.
echo [1/5] Adding files to git...
git add .

echo [2/5] Committing changes...
git commit -m "%COMMIT_MSG%"

echo [3/5] Creating Git tag %TAG_NAME%...
git tag %TAG_NAME%

echo [4/5] Pushing main branch to GitHub...
git push origin main

echo [5/5] Pushing tag %TAG_NAME% to GitHub...
git push origin %TAG_NAME%

echo.
echo ===================================================
echo   Release Successful! New Version: %TAG_NAME%
echo ===================================================
echo.
pause