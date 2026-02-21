-- 002_rls_policies.sql
-- Row-Level Security policies for Supabase
-- Permissive: service_role gets full access, anon gets read access

ALTER TABLE facilities      ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets          ENABLE ROW LEVEL SECURITY;
ALTER TABLE sensor_readings ENABLE ROW LEVEL SECURITY;

-- Allow full access via the service_role key (used by the backend)
CREATE POLICY "service_role_all" ON facilities      FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON assets          FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON sensor_readings FOR ALL USING (true) WITH CHECK (true);

-- Allow anonymous read access (for potential direct frontend queries)
CREATE POLICY "anon_read" ON facilities      FOR SELECT USING (true);
CREATE POLICY "anon_read" ON assets          FOR SELECT USING (true);
CREATE POLICY "anon_read" ON sensor_readings FOR SELECT USING (true);
