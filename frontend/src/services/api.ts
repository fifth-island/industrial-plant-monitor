/**
 * API service — hardcoded data layer for Vercel deployment.
 *
 * All functions return mock data from local TypeScript modules
 * instead of calling a remote backend.  The response shapes are
 * identical to the original FastAPI responses so components
 * remain unchanged.
 */

import type {
  FacilitiesListResponse,
  FacilitySummaryResponse,
  MetricName,
  TimeseriesResponse,
} from '../types';

import { facilitiesListResponse } from '../data/facilities';
import { summaries } from '../data/summaries';
import { generateTimeseries } from '../data/timeseries';

/** List all facilities. */
export async function fetchFacilities(): Promise<FacilitiesListResponse> {
  return facilitiesListResponse;
}

/** Summary / KPIs for a facility. */
export async function fetchSummary(
  facilityId: string,
  _hours: number = 24,
): Promise<FacilitySummaryResponse> {
  const summary = summaries[facilityId];
  if (!summary) throw new Error(`Facility ${facilityId} not found`);
  return summary;
}

/** Timeseries data for charts. */
export async function fetchTimeseries(
  facilityId: string,
  metric: MetricName = 'temperature',
  hours: number = 24,
  bucketMinutes: number = 5,
): Promise<TimeseriesResponse> {
  return generateTimeseries(facilityId, metric, hours, bucketMinutes);
}

