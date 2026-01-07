#!/bin/bash
#
# Pi Router - Update GitHub Repository Script
# This script commits and pushes changes to GitHub
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if git repository exists
if [ ! -d ".git" ]; then
    echo "Error: Not a git repository. Run ./scripts/setup-github.sh first."
    exit 1
fi

# Check for changes
if [ -z "$(git status --porcelain)" ]; then
    echo "No changes to commit. Working directory is clean."
    exit 0
fi

echo -e "${YELLOW}Changes detected:${NC}"
git status --short
echo ""

# Prompt for commit message
echo "Enter a commit message (empty to cancel):"
read -p "> " commit_message

if [ -z "$commit_message" ]; then
    echo "Commit cancelled."
    exit 0
fi

# Add all changes
git add .

# Show what will be committed
echo ""
echo -e "${YELLOW}Files to be committed:${NC}"
git status --short

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
