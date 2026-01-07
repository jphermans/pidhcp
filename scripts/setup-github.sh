#!/bin/bash
#
# Pi Router - GitHub Repository Setup Script
# This script helps you initialize and push your project to GitHub
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Pi Router - GitHub Setup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo -e "${RED}Git is not installed. Installing...${NC}"
    sudo apt-get update
    sudo apt-get install -y git
fi

# Check if we're in the project directory
if [ ! -f "backend/main.py" ] || [ ! -f "frontend/package.json" ]; then
    echo -e "${RED}Error: This script must be run from the project root directory${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1/6: Checking git status...${NC}"
if [ -d ".git" ]; then
    echo "Git repository already initialized"
    echo ""
    echo "Current git status:"
    git status
    echo ""
    read -p "Do you want to reinitialize git? This will remove all git history. (y/N): " reinit
    if [ "$reinit" = "y" ] || [ "$reinit" = "Y" ]; then
        rm -rf .git
        git init
        echo -e "${GREEN}Git reinitialized${NC}"
    fi
else
    git init
    echo -e "${GREEN}Git repository initialized${NC}"
fi

echo ""
echo -e "${YELLOW}Step 2/6: Adding files to git...${NC}"
git add .
git add -f .gitignore
echo -e "${GREEN}Files added to git${NC}"

echo ""
echo -e "${YELLOW}Step 3/6: Creating initial commit...${NC}"
if git rev-parse HEAD > /dev/null 2>&1; then
    echo "Commits already exist, skipping initial commit"
else
    git commit -m "Initial commit: Pi Router - Wi-Fi Router for Raspberry Pi 5

Features:
- Dual Wi-Fi operation (uplink + AP)
- DHCP/DNS server with dnsmasq
- NAT/routing with nftables
- Modern web UI (React + FastAPI)
- Captive portal support
- Device tracking with online/offline status
- System power control (reboot/shutdown)

JPHsystems 2026"
    echo -e "${GREEN}Initial commit created${NC}"
fi

echo ""
read -p "Enter your GitHub username: " github_username
read -p "Enter your repository name (e.g., pi-router): " repo_name

if [ -z "$github_username" ] || [ -z "$repo_name" ]; then
    echo -e "${RED}Error: GitHub username and repository name are required${NC}"
    exit 1
fi

REMOTE_URL="git@github.com:${github_username}/${repo_name}.git"

echo ""
echo -e "${YELLOW}Step 4/6: Adding GitHub remote...${NC}"
if git remote get-url origin &> /dev/null; then
    echo "Remote 'origin' already exists. Updating..."
    git remote set-url origin "$REMOTE_URL"
else
    git remote add origin "$REMOTE_URL"
fi
echo -e "${GREEN}Remote added: $REMOTE_URL${NC}"

echo ""
echo -e "${YELLOW}Step 5/6: Creating repository on GitHub...${NC}"
echo -e "${YELLOW}Please follow these steps:${NC}"
echo ""
echo "1. Go to https://github.com/new"
echo "2. Name your repository: $repo_name"
echo "3. Choose visibility: Private or Public"
echo "   - Note: Private is recommended for router config"
echo "4. DO NOT initialize with README, .gitignore, or license"
echo "5. Click 'Create repository'"
echo ""
read -p "Press Enter once you've created the repository on GitHub..."

echo ""
echo -e "${YELLOW}Step 6/6: Pushing to GitHub...${NC}"
echo ""
echo "Pushing to: $REMOTE_URL"
echo ""
echo "You may be asked for your GitHub credentials or SSH key passphrase..."
echo ""

BRANCH_NAME="main"
if git show-ref -q refs/heads/master; then
    BRANCH_NAME="master"
fi

git branch -M $BRANCH_NAME 2>/dev/null || true
git push -u origin $BRANCH_NAME

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Success! Repository pushed to GitHub${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Repository URL: https://github.com/${github_username}/${repo_name}"
    echo ""
    echo "To clone this repository on another machine:"
    echo "  git clone https://github.com/${github_username}/${repo_name}.git"
    echo ""
    echo "To update the repository later:"
    echo "  ./scripts/update-repo.sh"
else
    echo ""
    echo -e "${RED}Failed to push to GitHub${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Make sure you created the repository on GitHub first"
    echo "2. Check your SSH key is configured:"
    echo "   - Run: ssh -T git@github.com"
    echo "   - If that fails, you need to add SSH key to GitHub"
    echo "3. Or use HTTPS instead:"
    echo "   - Change remote URL to: https://github.com/${github_username}/${repo_name}.git"
    echo "   - Run: git remote set-url origin https://github.com/${github_username}/${repo_name}.git"
    echo "   - Push again"
    exit 1
fi

echo ""
echo -e "${GREEN}Done! Your Pi Router project is now on GitHub${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Star your repository on GitHub"
echo "2. Add a README with screenshots"
echo "3. Add a LICENSE file (MIT recommended)"
echo "4. Set up GitHub Releases for version tracking"
