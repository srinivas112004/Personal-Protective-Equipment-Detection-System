@echo off
echo ========================================
echo  FRESH PUSH TO GITHUB (Clean History)
echo ========================================
echo.
echo This will:
echo 1. Remove old git history
echo 2. Create fresh repository
echo 3. Push to GitHub with clean history
echo.
pause

cd /d "%~dp0"

echo.
echo Step 1: Removing old git folder...
rmdir /s /q .git 2>nul

echo Step 2: Initializing new repository...
git init

echo Step 3: Adding all files...
git add .

echo Step 4: Creating initial commit...
git commit -m "Initial commit: PPE Detection System with Flask UI and Modern Interface"

echo Step 5: Setting branch to main...
git branch -M main

echo Step 6: Adding remote repository...
git remote add origin https://github.com/srinivas112004/Personal-Protective-Equipment-Detection-System.git

echo Step 7: Force pushing to GitHub (overwrites history)...
git push -f origin main

echo.
echo ========================================
echo  SUCCESS! Repository updated with clean history
echo ========================================
echo.
echo Visit: https://github.com/srinivas112004/Personal-Protective-Equipment-Detection-System
echo.
pause
