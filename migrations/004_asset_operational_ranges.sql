-- 004_asset_operational_ranges.sql
-- Creates table for asset-specific operational ranges (min/max thresholds)
-- Each asset can have different acceptable ranges for temperature, pressure, power, production

CREATE TABLE IF NOT EXISTS asset_operational_ranges (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id     UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    metric_name  VARCHAR(100) NOT NULL,
    min_value    DOUBLE PRECISION NOT NULL,
    max_value    DOUBLE PRECISION NOT NULL,
    unit         VARCHAR(50) NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Ensure one range per asset per metric
    CONSTRAINT unique_asset_metric UNIQUE (asset_id, metric_name),
    
    -- Validate min < max
    CONSTRAINT valid_range CHECK (min_value < max_value)
);

-- Index for fast lookups during real-time checks
CREATE INDEX IF NOT EXISTS ix_operational_ranges_asset ON asset_operational_ranges (asset_id);

-- Index for queries by metric type
CREATE INDEX IF NOT EXISTS ix_operational_ranges_metric ON asset_operational_ranges (metric_name);
