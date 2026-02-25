/* ── Types mirroring the backend Pydantic schemas ── */

// GET /api/v1/facilities
export interface Facility {
  id: string;
  name: string;
  location: string;
  type: string;
  asset_count: number;
  created_at: string;
}

export interface FacilitiesListResponse {
  facilities: Facility[];
}

// GET /api/v1/dashboard/summary/{facility_id}
export interface MetricKPI {
  metric_name: string;
  current_value: number;
  avg_value: number;
  min_value: number;
  max_value: number;
  p50_value: number;
  p90_value: number;
  p95_value: number;
  unit: string;
}

export interface AssetStatus {
  id: string;
  name: string;
  type: string;
  status: 'operational' | 'maintenance';
  // Temperature
  temperature?: number | null;
  temperature_unit?: string | null;
  temperature_range?: { min: number; max: number };
  // Pressure
  pressure?: number | null;
  pressure_unit?: string | null;
  pressure_range?: { min: number; max: number };
  // Power
  power?: number | null;
  power_unit?: string | null;
  power_range?: { min: number; max: number };
  // Production
  production?: number | null;
  production_unit?: string | null;
  production_range?: { min: number; max: number };
}

export interface InsightItem {
  severity: 'ok' | 'low' | 'medium' | 'high';
  title: string;
  description: string;
  detected_at: string;
  asset_name?: string;
}

export interface FacilitySummaryResponse {
  facility_id: string;
  facility_name: string;
  location: string;
  facility_type: string;
  total_assets: number;
  operational_count: number;
  maintenance_count: number;
  active_alerts_count: number;
  kpis: MetricKPI[];
  insights: InsightItem[];
  assets: AssetStatus[];
  period_hours: number;
}

// GET /api/v1/dashboard/timeseries/{facility_id}
export interface TimeseriesPoint {
  timestamp: string;
  value: number;
}

export interface AssetTimeseries {
  asset_id: string;
  asset_name: string;
  data: TimeseriesPoint[];
}

export interface TimeseriesResponse {
  facility_id: string;
  facility_name: string;
  metric_name: string;
  unit: string;
  start: string;
  end: string;
  bucket_minutes: number;
  series: AssetTimeseries[];
}

// Available metrics
export type MetricName =
  | 'temperature'
  | 'pressure'
  | 'power_consumption'
  | 'production_output';

export const METRIC_LABELS: Record<MetricName, string> = {
  temperature: 'Temperature',
  pressure: 'Pressure',
  power_consumption: 'Power Consumption',
  production_output: 'Production Output',
};

export const METRIC_UNITS: Record<MetricName, string> = {
  temperature: '°C',
  pressure: 'bar',
  power_consumption: 'kW',
  production_output: 'units/hr',
};

export const METRIC_COLORS: Record<MetricName, string> = {
  temperature: '#f55330',     // Flamingo
  pressure: '#800139',        // Siren
  power_consumption: '#ffbc39', // Sunglow
  production_output: '#3f8600',
};
