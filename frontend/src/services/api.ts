import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import type {
  FacilitiesListResponse,
  FacilitySummaryResponse,
  MetricName,
  TimeseriesResponse,
} from '../types';

/* ---------- Axios instance ---------- */

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30_000, // 30 s — generous for Render cold-start
});

/* ---------- Retry interceptor (handles Render free-tier cold start) ---------- */

const MAX_RETRIES = 5;
const RETRY_DELAY_MS = 3_000; // initial delay, doubles each retry

interface RetryConfig extends InternalAxiosRequestConfig {
  __retryCount?: number;
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function shouldRetry(error: AxiosError): boolean {
  // Retry on network errors (ECONNABORTED, timeout, no response)
  if (!error.response) return true;
  // Retry on 500 / 502 / 503 / 504 (typical cold-start codes)
  const status = error.response.status;
  return status >= 500 && status <= 504;
}

api.interceptors.response.use(undefined, async (error: AxiosError) => {
  const config = error.config as RetryConfig | undefined;
  if (!config || !shouldRetry(error)) return Promise.reject(error);

  config.__retryCount = config.__retryCount ?? 0;
  if (config.__retryCount >= MAX_RETRIES) return Promise.reject(error);

  config.__retryCount += 1;
  const delay = RETRY_DELAY_MS * Math.pow(2, config.__retryCount - 1);
  console.warn(
    `[api] Retry ${config.__retryCount}/${MAX_RETRIES} in ${delay}ms → ${config.url}`,
  );
  await sleep(delay);
  return api.request(config);
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
