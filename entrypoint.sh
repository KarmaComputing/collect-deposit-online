exec uwsgi --http :80 --workers 1 --threads 2 --wsgi-file app.wsgi --touch-chain-reload subscribie.wsgi --chdir /usr/src/app/app

