#!/bin/bash

if [ "$1" == "" ];then
    echo 'missing arg: dbname'
    exit 1
fi

psql -c "create database $1"
litteralement schema both | psql -d "$1"
