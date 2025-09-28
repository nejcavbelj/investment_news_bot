#!/bin/bash
# Auto-update Investo from GitHub (safe version)

cd /home/pi/investment_news_bot || exit 1

# Test GitHub connection first
if ! ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
    echo "$(date): ❌ GitHub authentication failed. Check SSH keys or deploy key."
    exit 1
fi

# Always reset to avoid local conflicts
git fetch origin main
git reset --hard origin/main

echo "$(date): ✅ Updated to latest commit."
sudo systemctl restart investo.service

