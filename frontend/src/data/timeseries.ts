import type { MetricName, TimeseriesResponse } from '../types';
import { METRIC_UNITS } from '../types';
import { facilities } from './facilities';
import { summaries } from './summaries';

/* ──────────────────────────────────────────────
 * On-the-fly timeseries generator
 *
 * Ports the sinusoidal + noise approach from backend/app/seed.py
 * so charts look realistic without shipping large JSON blobs.
 * ────────────────────────────────────────────── */

/** Seeded pseudo-random number generator (mulberry32). */
function mulberry32(seed: number): () => number {
  let s = seed | 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Simple gaussian approximation from uniform RNG. */
function gaussianNoise(rng: () => number, stddev: number): number {
  // Box-Muller (simplified)
  const u1 = rng();
  const u2 = rng();
  const z = Math.sqrt(-2 * Math.log(u1 || 1e-10)) * Math.cos(2 * Math.PI * u2);
  return z * stddev;
}

/* ── Generators mirroring seed.py ── */

function generateTemperature(t: number, seed: number, rng: () => number): number {
  const base = 85 + 20 * Math.sin(seed + t / 3600);
  const noise = gaussianNoise(rng, 2.5);
  return Math.round(Math.max(60, Math.min(120, base + noise)) * 100) / 100;
}

function generatePressure(t: number, seed: number, rng: () => number): number {
  const base = 5.5 + 3.0 * Math.sin(seed + t / 7200);
  const noise = gaussianNoise(rng, 0.3);
  return Math.round(Math.max(1.0, Math.min(10.0, base + noise)) * 100) / 100;
}

function generatePower(t: number, seed: number, rng: () => number): number {
  const hourOfDay = (t / 3600) % 24;
  const dailyFactor = 0.6 + 0.4 * Math.exp(-((hourOfDay - 13) ** 2) / 20);
  const base = 300 * dailyFactor + 50 * Math.sin(seed + t / 1800);
  const noise = gaussianNoise(rng, 15);
  return Math.round(Math.max(100, Math.min(500, base + noise)) * 100) / 100;
}

function generateProduction(
  _t: number,
  _seed: number,
  rng: () => number,
  power: number,
): number {
  const ratio = (power - 100) / 400;
  const base = 50 + 150 * ratio;
  const noise = gaussianNoise(rng, 8);
  return Math.round(Math.max(50, Math.min(200, base + noise)) * 100) / 100;
}

/* ── Main generator ── */

export function generateTimeseries(
  facilityId: string,
  metric: MetricName,
  hours: number = 24,
  bucketMinutes: number = 5,
): TimeseriesResponse {
  const facility = facilities.find((f) => f.id === facilityId);
  const summary = summaries[facilityId];

  if (!facility || !summary) {
    return {
      facility_id: facilityId,
      facility_name: 'Unknown',
      metric_name: metric,
      unit: METRIC_UNITS[metric],
      start: new Date().toISOString(),
      end: new Date().toISOString(),
      bucket_minutes: bucketMinutes,
      series: [],
    };
  }

  const now = new Date();
  const startTime = new Date(now.getTime() - hours * 3600_000);
  const intervalMs = bucketMinutes * 60_000;
  const totalPoints = Math.floor((hours * 3600_000) / intervalMs);

  const series = summary.assets.map((asset, assetIdx) => {
    // Deterministic seed per (facility, asset, metric) so data is stable across calls
    const seedVal =
      (facilityId.charCodeAt(7) || 0) * 1000 +
      assetIdx * 100 +
      metric.charCodeAt(0);
    const rng = mulberry32(seedVal);
    // Advance RNG a bit so assets don't overlap
    for (let i = 0; i < assetIdx * 50; i++) rng();

    const assetSeed = rng() * 2 * Math.PI;

    const data: { timestamp: string; value: number }[] = [];
    for (let i = 0; i < totalPoints; i++) {
      const t = i * bucketMinutes * 60; // seconds elapsed
      const ts = new Date(startTime.getTime() + i * intervalMs);

      let value: number;
      switch (metric) {
        case 'temperature':
          value = generateTemperature(t, assetSeed, rng);
          break;
        case 'pressure':
          value = generatePressure(t, assetSeed, rng);
          break;
        case 'power_consumption':
          value = generatePower(t, assetSeed, rng);
          break;
        case 'production_output': {
          const power = generatePower(t, assetSeed, rng);
          value = generateProduction(t, assetSeed, rng, power);
          break;
        }
      }

      data.push({ timestamp: ts.toISOString(), value });
    }

    return {
      asset_id: asset.id,
      asset_name: asset.name,
      data,
    };
  });

  return {
    facility_id: facilityId,
    facility_name: facility.name,
    metric_name: metric,
    unit: METRIC_UNITS[metric],
    start: startTime.toISOString(),
    end: now.toISOString(),
    bucket_minutes: bucketMinutes,
    series,
  };
}
