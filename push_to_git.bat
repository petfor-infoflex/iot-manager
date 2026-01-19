@echo off
echo === IoT Manager - Git Push Script ===
echo.

cd /d "%~dp0"

:: Check if git is initialized
if not exist ".git" (
    echo Initializing git repository...
    git init
    git remote add origin git@github.com:petfor-infoflex/iot-manager.git
) else (
    echo Git repository already initialized.
)

:: Create .gitignore if it doesn't exist
if not exist ".gitignore" (
    echo Creating .gitignore...
    (
        echo # Python
        echo __pycache__/
        echo *.py[cod]
        echo *$py.class
        echo *.so
        echo .Python
        echo build/
        echo develop-eggs/
        echo dist/
        echo downloads/
        echo eggs/
        echo .eggs/
        echo lib/
        echo lib64/
        echo parts/
        echo sdist/
        echo var/
        echo wheels/
        echo *.egg-info/
        echo .installed.cfg
        echo *.egg
        echo.
        echo # Virtual environments
        echo venv/
        echo ENV/
        echo env/
        echo .venv/
        echo.
        echo # IDE
        echo .idea/
        echo .vscode/
        echo *.swp
        echo *.swo
        echo.
        echo # OS
        echo .DS_Store
        echo Thumbs.db
        echo.
        echo # App data
        echo *.log
        echo.
        echo # Settings ^(keep template, ignore user settings^)
        echo # settings.json
    ) > .gitignore
)

echo.
echo Adding files to staging...
git add .

echo.
echo Current status:
git status

echo.
set /p commit_msg="Enter commit message (or press Enter for default): "
if "%commit_msg%"=="" set commit_msg=Update IoT Manager

echo.
echo Committing with message: %commit_msg%
git commit -m "%commit_msg%"

echo.
echo Pushing to origin main...
git branch -M main
git push -u origin main

echo.
echo === Done! ===
pause
