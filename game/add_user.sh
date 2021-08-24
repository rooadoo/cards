#!/usr/bin/env bash
if [[ "$#" -eq 1 ]]; then
  USER=$1
else
  echo "invalid arguments, provide username to add"
fi

python manage.py shell -c "from add_user import add_user; add_user('$USER')"
