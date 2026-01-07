#!/bin/bash
#
# Pi Router - GitHub Synchronization Script
# This script synchronizes the Pi with the GitHub repository
# Pulls updates while preserving your data, or pushes local changes
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Pi Router - GitHub Sync${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if git repository exists
if [ ! -d ".git" ]; then
    echo -e "${RED}Error: Not a git repository${NC}"
    echo -e "Please run ./scripts/setup-github.sh first"
    exit 1
fi

# Show menu
echo "What would you like to do?"
echo ""
echo "  1) Pull updates from GitHub (recommended - keeps your data)"
echo "  2) Push local changes to GitHub"
echo "  3) Check status"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}Pulling updates from GitHub...${NC}"
        echo ""

        # Fetch latest
        git fetch origin

        # Check if there are changes
        CURRENT_COMMIT=$(git rev-parse HEAD)
        UPSTREAM_COMMIT=$(git rev-parse '@{u}')

        if [ "$CURRENT_COMMIT" = "$UPSTREAM_COMMIT" ]; then
            echo -e "${GREEN}Already up to date!${NC}"
            exit 0
        fi

        echo -e "${YELLOW}Changes found:${NC}"
        git log HEAD..@{u} --oneline
        echo ""

        # Pull changes
        echo -e "${YELLOW}Pulling changes...${NC}"
        git pull origin $(git rev-parse --abbrev-ref HEAD)

        # Rebuild frontend if changed
        if git diff --name-only HEAD@{1} HEAD | grep -q "^frontend/"; then
            echo ""
            echo -e "${YELLOW}Frontend files changed. Rebuilding...${NC}"
            cd frontend
            npm install --silent
            npm run build

            echo ""
            echo -e "${YELLOW}Copying frontend files...${NC}"
            sudo cp -r dist/* /opt/pi-router/frontend/dist/
        fi

        # Restart service if backend changed
        if git diff --name-only HEAD@{1} HEAD | grep -q "^backend/"; then
            echo ""
            echo -e "${YELLOW}Backend files changed. Restarting service...${NC}"
            sudo systemctl restart pi-router
        fi

        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}  Update complete!${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""
        echo -e "${GREEN}Your data is preserved in:${NC}"
        echo -e "  /var/lib/pi-router/data/"
        echo ""
        ;;

    2)
        echo ""
        echo -e "${YELLOW}Pushing changes to GitHub...${NC}"
        echo ""

        # Check for changes
        if [ -z "$(git status --porcelain | grep -v '??')" ]; then
            echo -e "${GREEN}No changes to commit${NC}"
            exit 0
        fi

        echo -e "${YELLOW}Changes detected:${NC}"
        git status --short
        echo ""

        # Prompt for commit message
        echo "Enter a commit message (empty to cancel):"
        read -p "> " commit_message

        if [ -z "$commit_message" ]; then
            echo "Push cancelled."
            exit 0
        fi

        # Add all changes (except ignored files)
        git add .

        # Commit
        echo ""
        echo -e "${YELLOW}Committing changes...${NC}"
        git commit -m "$commit_message"

        # Push
        echo ""
        echo -e "${YELLOW}Pushing to GitHub...${NC}"
        git push

        echo ""
        echo -e "${GREEN}Changes pushed to GitHub!${NC}"
        ;;

    3)
        echo ""
        echo -e "${YELLOW}Repository Status:${NC}"
        echo ""
        git status
        echo ""

        echo -e "${YELLOW}Recent Commits:${NC}"
        echo ""
        git log --oneline -5
        echo ""

        echo -e "${YELLOW}Branch:${NC} $(git rev-parse --abbrev-ref HEAD)"
        echo -e "${YELLOW}Remote:${NC} $(git remote get-url origin)"
        ;;

    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Persistent data location:${NC} /var/lib/pi-router/data/"
echo -e "${GREEN}Database:${NC} /var/lib/pi-router/data/pi-router.db"
echo ""
