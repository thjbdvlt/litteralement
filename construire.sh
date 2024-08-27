#!/bin/bash

if [ "$1" == "" ];then
    echo 'missing arg: dbname'
    exit 1
fi

psql -c "create database $1"
psql -d "$1" -f ./schema/tables.sql
psql -d "$1" -f ./schema/procedures/*.sql -f ./schema/indexes.sql -f ./schema/views/mots_phrases.sql -f ./schema/views/nonstopwords.sql -f ./schema/triggers.sql
