#!/bin/bash

# installer le module 'tokentype'

set -e

repo=https://github.com/thjbdvlt/tokentype
temp=/tmp/litteralement-installer

git clone $repo $temp

cd $temp

pip install .
