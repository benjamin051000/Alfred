#!/usr/bin/env bash

#TODO /shutdown alfred before committing. May cause some funky issues with voiceclients.
killall -9 python3
git pull
cd ..
./start.sh