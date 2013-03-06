#!/bin/sh

if test -f ~/setup.done; then
    exit 0;
fi

apt-get install -y postgresql
echo "listen_addresses = '*'" >> /etc/postgresql/9.1/main/postgresql.conf
echo "host all all 10.0.0.0/8 md5" >> /etc/postgresql/9.1/main/pg_hba.conf
service postgresql restart

sudo -u postgres psql template1 < schema.sql

touch ~/setup.done
