-- Initial database setup for Frete Sistema
-- This script runs when the PostgreSQL container is first created

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Set default encoding
SET client_encoding = 'UTF8';

-- Create custom functions for Brazilian text search
CREATE OR REPLACE FUNCTION unaccent_lower(text)
RETURNS text AS $$
BEGIN
    RETURN lower(unaccent($1));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create indexes for better performance
-- These will be created after tables are created by migrations

-- Create database backup user (read-only)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'backup_user') THEN
        CREATE USER backup_user WITH PASSWORD 'backup_pass_change_me';
        GRANT CONNECT ON DATABASE frete_sistema TO backup_user;
        GRANT USAGE ON SCHEMA public TO backup_user;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO backup_user;
    END IF;
END
$$;

-- Create monitoring user for Prometheus
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'prometheus_exporter') THEN
        CREATE USER prometheus_exporter WITH PASSWORD 'prom_pass_change_me';
        GRANT CONNECT ON DATABASE frete_sistema TO prometheus_exporter;
        GRANT USAGE ON SCHEMA public TO prometheus_exporter;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO prometheus_exporter;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO prometheus_exporter;
    END IF;
END
$$;

-- Performance settings
ALTER DATABASE frete_sistema SET random_page_cost = 1.1;
ALTER DATABASE frete_sistema SET effective_io_concurrency = 200;
ALTER DATABASE frete_sistema SET work_mem = '4MB';
ALTER DATABASE frete_sistema SET maintenance_work_mem = '64MB';
ALTER DATABASE frete_sistema SET shared_buffers = '256MB';

-- Create initial schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description) 
VALUES (1, 'Initial database setup') 
ON CONFLICT (version) DO NOTHING;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully';
END
$$;