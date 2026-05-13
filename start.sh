#!/bin/sh
set -e

# Run Liquibase migrations if the CLI and a JDBC URL are available.
# In local dev, migrations run via the separate liquibase compose service.
# In production (Railway), set DATABASE_URL and ensure liquibase is on PATH,
# or run migrations externally:
#
#   docker run --rm -v ./db:/liquibase/changelog \
#     -e DB_HOST=... -e DB_NAME=... -e DB_USER=... -e DB_PASSWORD=... \
#     liquibase/liquibase update

if [ -n "$RUN_MIGRATIONS" ] && command -v liquibase >/dev/null 2>&1; then
    echo "Running Liquibase migrations..."
    liquibase \
        --driver=org.postgresql.Driver \
        --url="jdbc:postgresql://${DB_HOST}:5432/${DB_NAME}" \
        --searchPath=/app/db/changelog \
        --changeLogFile=master.xml \
        --username="${DB_USER}" \
        --password="${DB_PASSWORD}" \
        update
fi

exec gunicorn --bind "0.0.0.0:${PORT:-5000}" backend.app:app
