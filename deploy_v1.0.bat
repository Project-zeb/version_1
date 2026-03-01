@echo off
REM ============================================================================
REM Save India v1.0 - Final Deployment Script (Windows Batch)
REM ============================================================================
REM This script prepares and pushes the v1.0 release to the Ayaan-v1.0 branch
REM
REM Prerequisites:
REM - Git installed and configured
REM - Remote repository set up
REM - You have push access to the repository
REM
REM Usage: Run this script in the version_1 directory
REM ============================================================================

ECHO.
ECHO ============================================================================
ECHO Save India v1.0 - Final Deployment Script
ECHO ============================================================================
ECHO.

REM Step 1: Verify current directory
ECHO [1/5] Verifying project directory...
IF NOT EXIST "app.py" (
   ECHO ERROR: app.py not found. Please run this script from the project root.
   PAUSE
   EXIT /B 1
)
IF NOT EXIST ".env.example" (
   ECHO ERROR: .env.example not found. Some setup files may be missing.
   PAUSE
   EXIT /B 1
)
ECHO ✓ Project directory verified

ECHO.
ECHO [2/5] Checking Git configuration...
git config user.name >nul 2>&1
IF ERRORLEVEL 1 (
   ECHO WARNING: Git user not configured
   ECHO Configure with: git config --global user.name "Your Name"
   ECHO              : git config --global user.email "your@email.com"
   ECHO.
)
git status >nul 2>&1
IF ERRORLEVEL 1 (
   ECHO ERROR: Not a valid git repository
   PAUSE
   EXIT /B 1
)
ECHO ✓ Git configuration verified

ECHO.
ECHO [3/5] Checking branch status...
git branch | findstr "Ayaan-v1.0" >nul 2>&1
IF ERRORLEVEL 1 (
   ECHO.
   ECHO Creating branch ayaan-v1.0...
    git checkout -b Ayaan-v1.0
   IF ERRORLEVEL 1 (
      ECHO ERROR: Failed to create branch
      PAUSE
      EXIT /B 1
   )
)
git branch | findstr "* Ayaan-v1.0" >nul 2>&1
IF ERRORLEVEL 1 (
   ECHO Switching to ayaan-v1.0 branch...
    git checkout Ayaan-v1.0
   IF ERRORLEVEL 1 (
      ECHO ERROR: Failed to switch branch
      PAUSE
      EXIT /B 1
   )
)
ECHO ✓ Currently on ayaan-v1.0 branch

ECHO.
ECHO [4/5] Staging changes for commit...
git add .
git status
ECHO.
SET /P CONFIRM="Proceed with commit? (Y/N): "
IF /I NOT "%CONFIRM%"=="Y" (
   ECHO Cancelled by user
   git reset
   PAUSE
   EXIT /B 1
)

ECHO.
ECHO Creating commit...
git commit -m "^
[FINAL] v1.0 Release - Complete documentation and database setup^
^
Changes:^
- Added comprehensive README.md with full system documentation^
- Created database_setup.sql for automated database initialization^
- Added .env.example configuration template^
- Created INSTALL_GUIDE.md with detailed installation steps^
- Added VERSION_HISTORY.md with commit history and release notes^
- Created FINAL_DEPLOYMENT_GUIDE.md for deployment instructions^
- All sensitive files properly configured in .gitignore^
^
Status: v1.0 is production-ready and stable^
Branch: ayaan-v1.0^
Latest: v2.0 on main branch"

IF ERRORLEVEL 1 (
   ECHO.
   ECHO Note: No changes to commit (already up to date)
)

ECHO.
ECHO [5/5] Pushing to remote repository...
ECHO.
ECHO Checking remote configuration...
git remote -v | findstr "origin" >nul 2>&1
IF ERRORLEVEL 1 (
   ECHO ERROR: No remote origin configured
   ECHO Configure with: git remote add origin ^<repository-url^>
   PAUSE
   EXIT /B 1
)

ECHO.
ECHO Pushing Ayaan-v1.0 branch...
git push -u origin Ayaan-v1.0

IF ERRORLEVEL 1 (
   ECHO.
   ECHO ERROR: Push failed
   ECHO Troubleshooting:
   ECHO - Check internet connection
   ECHO - Verify GitHub credentials/SSH keys
   ECHO - Check repository permissions
   PAUSE
   EXIT /B 1
)

ECHO.
ECHO ============================================================================
ECHO SUCCESS! v1.0 has been successfully pushed to ayaan-v1.0 branch
ECHO ============================================================================
ECHO.
ECHO Next steps:
ECHO 1. Visit: https://github.com/yourusername/Project-Zeb
ECHO 2. Switch to Ayaan-v1.0 branch
ECHO 3. Verify all files are present
ECHO 4. Review README.md for full documentation
ECHO 5. Share branch with team: https://github.com/yourusername/Project-Zeb/tree/Ayaan-v1.0
ECHO.
ECHO Documentation files created:
ECHO - README.md - Comprehensive project documentation
ECHO - INSTALL_GUIDE.md - Step-by-step installation guide
ECHO - VERSION_HISTORY.md - Commit history and version details
ECHO - FINAL_DEPLOYMENT_GUIDE.md - Detailed deployment instructions
ECHO - database_setup.sql - Automated database setup script
ECHO - .env.example - Environment configuration template
ECHO.
ECHO ============================================================================
PAUSE
