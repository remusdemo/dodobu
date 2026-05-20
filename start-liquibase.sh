#!/bin/sh

set -e

liquibase \
  --url="$LIQUIBASE_COMMAND_URL" \
  --username="$LIQUIBASE_COMMAND_USERNAME" \
  --password="$LIQUIBASE_COMMAND_PASSWORD" \
  --changeLogFile=db/changelog/master.xml \
  update
  