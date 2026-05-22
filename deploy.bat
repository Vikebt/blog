@echo off
title Blog Deploy Tool

echo ========================================
echo    Deploy Blog to GitHub Pages
echo ========================================
echo.

where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git not found. Install from: https://git-scm.com/
    pause
    exit /b 1
)

if exist .git (
    echo [INFO] Removing old .git folder...
    rmdir /s /q .git 2>nul
)

echo [INFO] Initializing Git repository...
git init
git checkout -b main
git add .
git commit -m "Initial blog setup"

set /p GH_USER=Enter your GitHub username (Vikebt):
set /p GH_TOKEN=Enter your GitHub Personal Access Token:
set /p REPO=Enter repository name (press Enter for default: blog):
if "%REPO%"=="" set REPO=blog

echo.
echo [INFO] Configuring remote...
git remote add origin https://%GH_USER%:%GH_TOKEN%@github.com/%GH_USER%/%REPO%.git

echo.
echo [INFO] Pushing to GitHub...
git push -u origin main --force

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo      DEPLOY SUCCESSFUL!
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Go to: https://github.com/%GH_USER%/%REPO%/settings/pages
    echo 2. Under "Source", select "GitHub Actions"
    echo 3. Wait 1-2 minutes for the build
    echo.
    echo Your blog will be at:
    echo   https://%GH_USER%.github.io/%REPO%/
    echo.
    echo To add new posts:
    echo   1. Write a .md file in content/posts/
    echo   2. Run: deploy.bat
) else (
    echo.
    echo [FAILED] Check your username and token.
    echo Make sure you created the repository on GitHub first.
    echo.
    echo Open: https://github.com/new
    echo Repository name: %REPO%  (Public)
)

pause
