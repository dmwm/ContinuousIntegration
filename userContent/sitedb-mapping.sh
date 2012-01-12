#!/bin/sh
set -e

mapping=$1
db=$2


sqlite3 $db "insert into user_group values (2, 'dataops')"
sqlite3 $db "insert into role values (2, 'developer')"

IFS=$'\n'
for i in $(cat $mapping); do
  export IFS=,
  set $i
  id=$1
  forename=$2
  surname=$3
  username=$4
  dn=$5

  sqlite3 $db "insert into contact values($id, '$forename', '$surname', '$username', '$dn')"
  sqlite3 $db "insert into group_responsibility values($id,2,2)"
done

unset IFS
