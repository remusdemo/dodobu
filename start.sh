#!/bin/sh
set -e

if [ "${SERVICE_ROLE}" = "worker" ]; then
    exec python worker.py
else
    exec gunicorn --bind "0.0.0.0:${PORT:-5000}" --workers 4 --timeout 30 backend.app:app
fi
