-- init.sql — runs automatically on first container start
-- Creates the full schema: facilities, assets, sensor_readings,
-- operational_insights, asset_operational_ranges

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Core tables ──────────────────────────────────────

-- Facilities
CREATE TABLE IF NOT EXISTS facilities (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(255) NOT NULL,
    location    VARCHAR(255) NOT NULL,
    type        VARCHAR(100) NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Assets
CREATE TABLE IF NOT EXISTS assets (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id  UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    name         VARCHAR(255) NOT NULL,
    type         VARCHAR(100) NOT NULL,
    status       VARCHAR(50)  NOT NULL DEFAULT 'operational',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Sensor Readings
CREATE TABLE IF NOT EXISTS sensor_readings (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id     UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    metric_name  VARCHAR(100)     NOT NULL,
    value        DOUBLE PRECISION NOT NULL,
    unit         VARCHAR(50)      NOT NULL,
    timestamp    TIMESTAMPTZ      NOT NULL,
    created_at   TIMESTAMPTZ      NOT NULL DEFAULT now()
);

-- ── Operational insights (alert tracking) ────────────

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

-- ── Asset operational ranges (threshold config) ──────

CREATE TABLE IF NOT EXISTS asset_operational_ranges (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id     UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    metric_name  VARCHAR(100) NOT NULL,
    min_value    DOUBLE PRECISION NOT NULL,
    max_value    DOUBLE PRECISION NOT NULL,
    unit         VARCHAR(50) NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT unique_asset_metric UNIQUE (asset_id, metric_name),
    CONSTRAINT valid_range CHECK (min_value < max_value)
);

-- ── Indexes ──────────────────────────────────────────

CREATE INDEX IF NOT EXISTS ix_readings_asset_metric_ts ON sensor_readings (asset_id, metric_name, timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_readings_timestamp        ON sensor_readings (timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_assets_facility           ON assets (facility_id);

CREATE INDEX IF NOT EXISTS ix_insights_facility_active ON operational_insights (facility_id, is_active, detected_at DESC);
CREATE INDEX IF NOT EXISTS ix_insights_asset ON operational_insights (asset_id) WHERE asset_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ix_insights_active_unique
    ON operational_insights (facility_id, metric_name, threshold_type, COALESCE(asset_id, '00000000-0000-0000-0000-000000000000'::uuid))
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS ix_operational_ranges_asset  ON asset_operational_ranges (asset_id);
CREATE INDEX IF NOT EXISTS ix_operational_ranges_metric ON asset_operational_ranges (metric_name);

-- ── Triggers ─────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_insights_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_insights_updated_at'
    ) THEN
        CREATE TRIGGER trg_insights_updated_at
            BEFORE UPDATE ON operational_insights
            FOR EACH ROW
            EXECUTE FUNCTION update_insights_updated_at();
    END IF;
END;
$$;
