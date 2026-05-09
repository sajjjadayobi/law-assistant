#!/bin/bash
# Creates the phoenix database if it does not already exist.
# Docker Postgres entrypoint runs this as the postgres superuser.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  SELECT 'CREATE DATABASE phoenix OWNER phoenix ENCODING ''UTF8'''
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'phoenix')\gexec
  GRANT CONNECT ON DATABASE phoenix TO phoenix;
EOSQL
