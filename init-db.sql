-- ============================================================================
-- Database Initialization for Law Agent Deployment
-- This script runs once at first container start (empty data volume).
-- Creates the phoenix role used by the Phoenix observability service.
-- CREATE DATABASE phoenix is handled by init-db.sh (shell scripts can run
-- outside a transaction block; SQL init files cannot).
-- ============================================================================

-- Create phoenix role (idempotent)
DO $$
BEGIN
  CREATE ROLE phoenix WITH LOGIN PASSWORD 'phoenix_password';
EXCEPTION WHEN duplicate_object THEN
  NULL;
END
$$;
