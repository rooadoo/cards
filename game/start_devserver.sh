#!/usr/bin/env bash

docker run --rm --name redis_devserver -d -p 127.0.0.1:6379:6379 redis
python3 manage.py makemigrations --noinput
python3 manage.py migrate --noinput
python3 manage.py shell -c "from setup import populate_db;populate_db()"
DJANGO_ALLOWED_HOSTS=127.0.0.1 REDIS_HOST=127.0.0.1 python3 manage.py runserver
docker kill redis_devserver
