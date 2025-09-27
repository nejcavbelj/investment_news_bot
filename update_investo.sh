#!/bin/bash
cd /home/pi/Investo
git fetch origin master
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/master)

if [ $LOCAL != $REMOTE ]; then
    echo "Updating Investo..."
    git pull
    sudo systemctl restart investo.service
else
    echo "Investo is already up to date."
fi
