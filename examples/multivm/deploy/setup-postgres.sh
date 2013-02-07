#!/bin/sh

yum install -y postgresql-server postgresql-devel
postgresql-setup initdb
echo "listen_addresses = '*'" >> /var/lib/pgsql/data/postgresql.conf
echo "host all all 10.0.0.0/8 md5" >> /var/lib/pgsql/data/pg_hba.conf
systemctl start postgresql.service
sudo -u postgres psql template1 <<EOM
  create user blog with password 'Ravello';
  create database blog owner blog;
EOM
