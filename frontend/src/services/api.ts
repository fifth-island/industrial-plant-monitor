import axios from 'axios';
import type {
  FacilitiesListResponse,
  FacilitySummaryResponse,
  MetricName,
  TimeseriesResponse,
} from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 15_000,
});

/** List all facilities. */
export async function fetchFacilities(): Promise<FacilitiesListResponse> {
  const { data } = await api.get<FacilitiesListResponse>('/facilities');
  return data;
}

/** Summary / KPIs for a facility. */
export async function fetchSummary(
  facilityId: string,
  hours: number = 24,
): Promise<FacilitySummaryResponse> {
  const { data } = await api.get<FacilitySummaryResponse>(
    `/dashboard/summary/${facilityId}`,
    { params: { hours } },
  );
  return data;
}

/** Timeseries data for charts. */
export async function fetchTimeseries(
  facilityId: string,
  metric: MetricName = 'temperature',
  hours: number = 24,
  bucketMinutes: number = 5,
): Promise<TimeseriesResponse> {
  const { data } = await api.get<TimeseriesResponse>(
    `/dashboard/timeseries/${facilityId}`,
    { params: { metric, hours, bucket_minutes: bucketMinutes } },
  );
  return data;
}
