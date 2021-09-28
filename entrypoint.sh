#!/usr/bin/env bash
exec uwsgi --http :80 --workers 1 --threads 2 --wsgi-file app.wsgi --touch-chain-reload app.wsgi --chdir /usr/src/app/

