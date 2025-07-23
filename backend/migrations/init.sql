-- Initial database setup for Romanian Freight Forwarder system
-- This script runs automatically when PostgreSQL container starts

-- Create PostGIS extension for geographic data
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create custom enum types that need to be available before migrations
DO $$
BEGIN
    -- Order status enum
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
        CREATE TYPE orderstatus AS ENUM (
            'pending',
            'assigned', 
            'in_transit',
            'awaiting_documents',
            'documents_received',
            'documents_validated',
            'client_invoiced',
            'payment_received',
            'subcontractor_paid',
            'completed',
            'cancelled',
            'disputed'
        );
    END IF;
    
    -- User role enum
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
        CREATE TYPE userrole AS ENUM (
            'admin',
            'dispatcher',
            'accountant',
            'viewer'
        );
    END IF;
    
    -- Document type enum  
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'documenttype') THEN
        CREATE TYPE documenttype AS ENUM (
            'invoice',
            'pod',
            'transport_order',
            'client_invoice',
            'additional'
        );
    END IF;
END$$;

-- Create indexes for geographic operations
-- These will be created after tables are made by Alembic

-- Set timezone for consistency
SET timezone TO 'UTC';

-- Create logistics user permissions (if running as superuser)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'logistics') THEN
        CREATE ROLE logistics WITH LOGIN PASSWORD 'password';
    END IF;
END$$;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO logistics;
GRANT CREATE ON SCHEMA public TO logistics;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO logistics;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO logistics;

-- Set default permissions for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO logistics;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO logistics;
