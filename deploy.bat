@echo off
cd /d "%~dp0"
echo.
echo Starting deploy...
echo.

where git >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Git not found. Install from https://git-scm.com/
    pause
    exit
)

if not exist .git goto firsttime

:quick
echo Quick mode - pushing changes...
git add .
git add -A 2>nul
git diff --cached --quiet 2>nul
if %errorlevel% equ 0 (
    echo No changes to push.
    pause
    exit
)
git commit -m "Update blog"
git push
echo.
echo Done!
pause
exit

:firsttime
echo First time setup - please enter your info:
set /p GH_USER=GitHub username:
set /p GH_TOKEN=GitHub token:
set REPO=blog

git init
git checkout -b main
git add .
git commit -m "Initial blog setup"
git remote add origin https://%GH_USER%:%GH_TOKEN%@github.com/%GH_USER%/%REPO%.git
git push -u origin main --force
echo.
echo Done! Next time just double-click this file.
pause
