#!/usr/bin/env bash

cd lavalink
echo Be sure you have Java version 11 or greater.
pm2 start java -jar Lavalink.jar

cd ..

cd src
pm2 start main.py --interpreter=python3
