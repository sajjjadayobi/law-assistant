-- Initialize Phoenix database on postgres startup
-- This script creates the phoenix user and database if they don't exist

-- Create phoenix user if not exists
DO
$$
BEGIN
  CREATE ROLE phoenix WITH LOGIN PASSWORD 'phoenix_password';
EXCEPTION WHEN duplicate_object THEN
  RAISE NOTICE 'Role phoenix already exists';
END
$$;

-- Create phoenix database if not exists
CREATE DATABASE phoenix
  WITH
  OWNER = phoenix
  ENCODING = 'UTF8'
  LC_COLLATE = 'en_US.UTF-8'
  LC_CTYPE = 'en_US.UTF-8'
  TEMPLATE = template0;

-- Grant privileges
GRANT CONNECT ON DATABASE phoenix TO phoenix;
GRANT CONNECT ON DATABASE law_agent TO postgres;

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO phoenix;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO phoenix;
