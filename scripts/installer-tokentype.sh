#!/bin/bash

# installer le module 'tokentype'
repo1=https://github.com/thjbdvlt/tokentype
temp=/tmp/litteralement-installer
git clone $repo1 $temp
cd $temp
pip install .
