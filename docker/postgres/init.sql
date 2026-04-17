-- PostgreSQL initialization script for Kuwait WhatsApp Growth Engine
-- This runs once when the database container is first created.

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create application role for RLS enforcement
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user LOGIN PASSWORD 'app_user_password';
    END IF;
END
$$;

-- Grant permissions to app_user
GRANT CONNECT ON DATABASE kwgrowth TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;

-- RLS helper: Enable RLS on a table with tenant isolation
-- Usage: SELECT enable_rls('table_name');
CREATE OR REPLACE FUNCTION enable_rls(table_name TEXT) RETURNS void AS $$
BEGIN
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);

    -- SELECT/UPDATE/DELETE policy
    EXECUTE format(
        'CREATE POLICY tenant_isolation_policy ON %I
         FOR ALL
         USING (company_id = current_setting(''app.current_tenant'')::uuid)',
        table_name
    );

    -- INSERT policy
    EXECUTE format(
        'CREATE POLICY tenant_insert_policy ON %I
         FOR INSERT
         WITH CHECK (company_id = current_setting(''app.current_tenant'')::uuid)',
        table_name
    );
END;
$$ LANGUAGE plpgsql;

-- Auto-update updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Helper to add updated_at trigger to a table
CREATE OR REPLACE FUNCTION add_updated_at_trigger(table_name TEXT) RETURNS void AS $$
BEGIN
    EXECUTE format(
        'CREATE TRIGGER set_updated_at
         BEFORE UPDATE ON %I
         FOR EACH ROW
         EXECUTE FUNCTION update_updated_at_column()',
        table_name
    );
END;
$$ LANGUAGE plpgsql;
