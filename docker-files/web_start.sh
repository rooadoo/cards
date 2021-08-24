#!/usr/bin/env bash

touch table/migrations/__init__.py
python3 manage.py makemigrations --noinput
python3 manage.py migrate --noinput
python3 manage.py collectstatic --clear --noinput
python3 manage.py shell -c "from setup import populate_db;populate_db()"
gunicorn --bind :8000 --workers 3 --threads 2 \
  --access-logfile /var/log/mnt/gunicorn_access.log \
  --error-logfile /var/log/mnt/gunicorn_error.log \
  --access-logformat '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"' \
  table.wsgi:application
