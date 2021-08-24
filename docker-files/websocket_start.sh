#!/usr/bin/env bash

daphne -b 0.0.0.0 -p 5000  --proxy-headers --access-log /var/log/mnt/daphne_access.log table.asgi:application
