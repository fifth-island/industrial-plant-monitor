-- 003_create_insights_table.sql
-- Creates operational_insights table for persistent alert tracking

CREATE TABLE IF NOT EXISTS operational_insights (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id     UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    asset_id        UUID REFERENCES assets(id) ON DELETE CASCADE,
    severity        VARCHAR(20) NOT NULL CHECK (severity IN ('ok', 'low', 'medium', 'high')),
    title           VARCHAR(255) NOT NULL,
    description     TEXT NOT NULL,
    metric_name     VARCHAR(100) NOT NULL,
    threshold_type  VARCHAR(50),
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS ix_insights_facility_active ON operational_insights (facility_id, is_active, detected_at DESC);
CREATE INDEX IF NOT EXISTS ix_insights_asset ON operational_insights (asset_id) WHERE asset_id IS NOT NULL;

-- Unique constraint to prevent duplicate active insights for same issue
CREATE UNIQUE INDEX IF NOT EXISTS ix_insights_active_unique 
    ON operational_insights (facility_id, metric_name, threshold_type, COALESCE(asset_id, '00000000-0000-0000-0000-000000000000'::uuid))
    WHERE is_active = true;

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_insights_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_insights_updated_at
    BEFORE UPDATE ON operational_insights
    FOR EACH ROW
    EXECUTE FUNCTION update_insights_updated_at();
