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
  unit: string;
}

export interface AssetStatus {
  id: string;
  name: string;
  type: string;
  status: 'operational' | 'maintenance';
}

export interface FacilitySummaryResponse {
  facility_id: string;
  facility_name: string;
  location: string;
  facility_type: string;
  total_assets: number;
  operational_count: number;
  maintenance_count: number;
  kpis: MetricKPI[];
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
  temperature: '#ff4d4f',
  pressure: '#1890ff',
  power_consumption: '#faad14',
  production_output: '#52c41a',
};
