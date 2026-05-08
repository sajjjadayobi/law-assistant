-- ============================================================================
-- Database Initialization for Law Agent Deployment
-- Creates Phoenix database and user, sets up law_agent database
-- ============================================================================

-- Create phoenix user if not exists
DO
$$
BEGIN
  CREATE ROLE phoenix WITH LOGIN PASSWORD 'phoenix_password';
  RAISE NOTICE 'Created role: phoenix';
EXCEPTION WHEN duplicate_object THEN
  RAISE NOTICE 'Role phoenix already exists';
END
$$;

-- Create phoenix database if not exists
DO
$$
BEGIN
  CREATE DATABASE phoenix
    WITH
    OWNER = phoenix
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;
  RAISE NOTICE 'Created database: phoenix';
EXCEPTION WHEN duplicate_object THEN
  RAISE NOTICE 'Database phoenix already exists';
END
$$;

-- Grant privileges to phoenix user
GRANT CONNECT ON DATABASE phoenix TO phoenix;
GRANT CONNECT ON DATABASE law_agent TO postgres;

-- Set default privileges for new objects in phoenix database
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO phoenix;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO phoenix;
