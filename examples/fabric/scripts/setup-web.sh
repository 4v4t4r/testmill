#!/bin/sh

if test -f ~/setup.done; then
    exit 0;
fi

apt-get install -y python-psycopg2 gunicorn

touch ~/setup.done
