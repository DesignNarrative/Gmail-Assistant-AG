-- =============================================================================
-- Abhinav Group — AI Gmail Intelligence Assistant
-- PostgreSQL Initialization Script
-- Runs automatically when PostgreSQL container first starts
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- Fuzzy text search
CREATE EXTENSION IF NOT EXISTS "unaccent";     -- Accent-insensitive search
CREATE EXTENSION IF NOT EXISTS "vector";       -- pgvector for embeddings

-- Create application schema
CREATE SCHEMA IF NOT EXISTS abhinav;

-- Set default search path
ALTER DATABASE abhinav_ai SET search_path TO public, abhinav;

-- Create application-specific role (read-only for reporting)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'abhinav_readonly') THEN
    CREATE ROLE abhinav_readonly;
  END IF;
END
$$;

-- Grant read permissions to readonly role
GRANT CONNECT ON DATABASE abhinav_ai TO abhinav_readonly;
GRANT USAGE ON SCHEMA public TO abhinav_readonly;

-- Performance settings for the database
-- These will be applied on next connection
COMMENT ON DATABASE abhinav_ai IS 'Abhinav Group AI Intelligence Assistant — Primary Database';
