#!/usr/bin/env bash

# Recommended: Use /shutdown alfred before committing. May cause some funky issues with voiceclients.
killall -9 python3
git pull
cd ..
pip3 install -r requirements.txt
./start.sh
