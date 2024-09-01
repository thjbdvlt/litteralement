#!/bin/bash

if [ "$1" == "" ];then
    echo 'missing arg: dbname'
    exit 1
fi

psql -c "create database $1"
psql -d "$1" -f ./litteralement/schemas/litteralement.sql -f ./litteralement/schemas/eav.sql
