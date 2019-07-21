#!/usr/bin/env bash

#TODO /shutdown alfred before committing. May cause some funky issues with voiceclients.
killall -v python3 main.py
cd ../src
git pull
../start.sh
