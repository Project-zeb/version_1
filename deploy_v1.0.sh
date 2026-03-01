#!/bin/bash

################################################################################
# Save India v1.0 - Final Deployment Script (Bash for macOS/Linux)
################################################################################
# This script prepares and pushes the v1.0 release to the Ayaan-v1.0 branch
#
# Prerequisites:
# - Git installed and configured
# - Remote repository set up
# - You have push access to the repository
# - Script must be executable: chmod +x deploy_v1.0.sh
#
# Usage: ./deploy_v1.0.sh
################################################################################

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "================================================================================"
echo "Save India v1.0 - Final Deployment Script"
echo "================================================================================"
echo ""

# Step 1: Verify current directory
echo "[1/5] Verifying project directory..."
if [ ! -f "app.py" ]; then
   echo -e "${RED}ERROR: app.py not found. Please run this script from the project root.${NC}"
   exit 1
fi
if [ ! -f ".env.example" ]; then
   echo -e "${RED}ERROR: .env.example not found. Some setup files may be missing.${NC}"
   exit 1
fi
echo -e "${GREEN}✓ Project directory verified${NC}"

echo ""
echo "[2/5] Checking Git configuration..."
if ! git config user.name > /dev/null 2>&1; then
   echo -e "${YELLOW}WARNING: Git user not configured${NC}"
   echo "Configure with:"
   echo "  git config --global user.name \"Your Name\""
   echo "  git config --global user.email \"your@email.com\""
   echo ""
fi
if ! git status > /dev/null 2>&1; then
   echo -e "${RED}ERROR: Not a valid git repository${NC}"
   exit 1
fi
echo -e "${GREEN}✓ Git configuration verified${NC}"

echo ""
echo "[3/5] Checking branch status..."
if ! git branch | grep -q "Ayaan-v1.0"; then
   echo "Creating branch Ayaan-v1.0..."
   git checkout -b Ayaan-v1.0
   if [ $? -ne 0 ]; then
      echo -e "${RED}ERROR: Failed to create branch${NC}"
      exit 1
   fi
fi
if ! git branch | grep -q "^\* Ayaan-v1.0"; then
   echo "Switching to Ayaan-v1.0 branch..."
   git checkout Ayaan-v1.0
   if [ $? -ne 0 ]; then
      echo -e "${RED}ERROR: Failed to switch branch${NC}"
      exit 1
   fi
fi
echo -e "${GREEN}✓ Currently on ayaan-v1.0 branch${NC}"

echo ""
echo "[4/5] Staging changes for commit..."
git add .
echo "Current git status:"
git status
echo ""
read -p "Proceed with commit? (Y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
   echo "Cancelled by user"
   git reset
   exit 0
fi

echo ""
echo "Creating commit..."
git commit -m "[FINAL] v1.0 Release - Complete documentation and database setup

Changes:
- Added comprehensive README.md with full system documentation
- Created database_setup.sql for automated database initialization
- Added .env.example configuration template
- Created INSTALL_GUIDE.md with detailed installation steps
- Added VERSION_HISTORY.md with commit history and release notes
- Created FINAL_DEPLOYMENT_GUIDE.md for deployment instructions
- All sensitive files properly configured in .gitignore

Status: v1.0 is production-ready and stable
Branch: Ayaan-v1.0
Latest: v2.0 on main branch" || {
   echo ""
   echo "Note: No changes to commit (already up to date)"
}

echo ""
echo "[5/5] Pushing to remote repository..."
echo ""
echo "Checking remote configuration..."
if ! git remote -v | grep -q "origin"; then
   echo -e "${RED}ERROR: No remote origin configured${NC}"
   echo "Configure with: git remote add origin <repository-url>"
   exit 1
fi

echo ""
echo "Pushing Ayaan-v1.0 branch..."
if ! git push -u origin Ayaan-v1.0; then
   echo ""
   echo -e "${RED}ERROR: Push failed${NC}"
   echo "Troubleshooting:"
   echo "- Check internet connection"
   echo "- Verify GitHub credentials/SSH keys"
   echo "- Check repository permissions"
   exit 1
fi

echo ""
echo "================================================================================"
echo -e "${GREEN}SUCCESS! v1.0 has been successfully pushed to ayaan-v1.0 branch${NC}"
echo "================================================================================"
echo ""
echo "Next steps:"
echo "1. Visit: https://github.com/yourusername/Project-Zeb"
echo "2. Switch to Ayaan-v1.0 branch"
echo "3. Verify all files are present"
echo "4. Review README.md for full documentation"
echo "5. Share branch with team: https://github.com/yourusername/Project-Zeb/tree/Ayaan-v1.0"
echo ""
echo "Documentation files created:"
echo "- README.md - Comprehensive project documentation"
echo "- INSTALL_GUIDE.md - Step-by-step installation guide"
echo "- VERSION_HISTORY.md - Commit history and version details"
echo "- FINAL_DEPLOYMENT_GUIDE.md - Detailed deployment instructions"
echo "- database_setup.sql - Automated database setup script"
echo "- .env.example - Environment configuration template"
echo ""
echo "================================================================================"
