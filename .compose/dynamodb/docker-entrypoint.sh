#!/bin/sh
set -eu

mkdir -p /home/dynamodblocal/data
chown -R dynamodblocal:dynamodblocal /home/dynamodblocal/data

exec runuser -u dynamodblocal -- java "$@"
