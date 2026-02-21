-- 001_create_tables.sql
-- Creates the core schema: facilities, assets, sensor_readings

-- Enable UUID extension (Supabase enables this by default)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Facilities
CREATE TABLE facilities (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(255) NOT NULL,
    location    VARCHAR(255) NOT NULL,
    type        VARCHAR(100) NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Assets
CREATE TABLE assets (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    facility_id  UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    name         VARCHAR(255) NOT NULL,
    type         VARCHAR(100) NOT NULL,
    status       VARCHAR(50)  NOT NULL DEFAULT 'operational',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Sensor Readings
CREATE TABLE sensor_readings (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id     UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    metric_name  VARCHAR(100)     NOT NULL,
    value        DOUBLE PRECISION NOT NULL,
    unit         VARCHAR(50)      NOT NULL,
    timestamp    TIMESTAMPTZ      NOT NULL,
    created_at   TIMESTAMPTZ      NOT NULL DEFAULT now()
);

-- Indexes for query performance
CREATE INDEX ix_readings_asset_metric_ts ON sensor_readings (asset_id, metric_name, timestamp DESC);
CREATE INDEX ix_readings_timestamp        ON sensor_readings (timestamp DESC);
CREATE INDEX ix_assets_facility           ON assets (facility_id);
