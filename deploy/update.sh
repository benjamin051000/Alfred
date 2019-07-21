#!/usr/bin/env bash

#Should kill main.py TODO be more specific
kill -9 python
cd ../src
git pull
../start.sh
