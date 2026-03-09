import type {
  FacilitySummaryResponse,
  AssetStatus,
  MetricKPI,
  InsightItem,
} from '../types';
import { FACILITY_IDS } from './facilities';

/* ──────────────────────────────────────────────
 * Asset definitions per facility
 * (mirrors backend/app/seed.py)
 * ────────────────────────────────────────────── */

interface AssetDef {
  id: string;
  name: string;
  type: string;
  ranges: {
    temperature: { min: number; max: number };
    pressure: { min: number; max: number };
    power_consumption: { min: number; max: number };
    production_output: { min: number; max: number };
  };
}

const ASSET_TYPE_RANGES: Record<string, AssetDef['ranges']> = {
  turbine:             { temperature: { min: 60, max: 115 }, pressure: { min: 1, max: 10 }, power_consumption: { min: 100, max: 500 }, production_output: { min: 50, max: 200 } },
  boiler:              { temperature: { min: 65, max: 125 }, pressure: { min: 2, max: 10 }, power_consumption: { min: 150, max: 500 }, production_output: { min: 50, max: 200 } },
  generator:           { temperature: { min: 60, max: 110 }, pressure: { min: 1, max: 9 },  power_consumption: { min: 100, max: 500 }, production_output: { min: 60, max: 200 } },
  cooling_tower:       { temperature: { min: 50, max: 100 }, pressure: { min: 1, max: 8 },  power_consumption: { min: 100, max: 400 }, production_output: { min: 50, max: 180 } },
  reactor:             { temperature: { min: 70, max: 130 }, pressure: { min: 2, max: 10 }, power_consumption: { min: 150, max: 500 }, production_output: { min: 50, max: 200 } },
  compressor:          { temperature: { min: 60, max: 115 }, pressure: { min: 3, max: 10 }, power_consumption: { min: 150, max: 500 }, production_output: { min: 50, max: 200 } },
  distillation_column: { temperature: { min: 65, max: 120 }, pressure: { min: 1, max: 9 },  power_consumption: { min: 120, max: 480 }, production_output: { min: 50, max: 200 } },
  heat_exchanger:      { temperature: { min: 60, max: 115 }, pressure: { min: 1, max: 9 },  power_consumption: { min: 100, max: 450 }, production_output: { min: 50, max: 200 } },
  pump:                { temperature: { min: 55, max: 105 }, pressure: { min: 2, max: 10 }, power_consumption: { min: 100, max: 400 }, production_output: { min: 50, max: 180 } },
  cnc_machine:         { temperature: { min: 60, max: 110 }, pressure: { min: 1, max: 8 },  power_consumption: { min: 120, max: 480 }, production_output: { min: 60, max: 200 } },
  robot:               { temperature: { min: 55, max: 105 }, pressure: { min: 1, max: 7 },  power_consumption: { min: 100, max: 450 }, production_output: { min: 50, max: 190 } },
  conveyor:            { temperature: { min: 50, max: 100 }, pressure: { min: 1, max: 6 },  power_consumption: { min: 80, max: 350 },  production_output: { min: 50, max: 180 } },
  furnace:             { temperature: { min: 70, max: 130 }, pressure: { min: 1, max: 9 },  power_consumption: { min: 200, max: 500 }, production_output: { min: 50, max: 200 } },
};

/* ── Seeded pseudo-random (deterministic per asset) ── */
function seededRandom(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return s / 2147483647;
  };
}

function randomInRange(rng: () => number, min: number, max: number): number {
  return Math.round((min + rng() * (max - min)) * 100) / 100;
}

/* ── Build assets per facility ── */

function makeAssets(
  defs: { name: string; type: string }[],
  facilityIndex: number,
): AssetStatus[] {
  return defs.map((d, i) => {
    const ranges = ASSET_TYPE_RANGES[d.type] ?? ASSET_TYPE_RANGES.turbine;
    const rng = seededRandom(facilityIndex * 100 + i + 42);
    // ~12% chance of maintenance
    const status: 'operational' | 'maintenance' =
      rng() < 0.12 ? 'maintenance' : 'operational';

    return {
      id: `a${String(facilityIndex).padStart(2, '0')}${String(i + 1).padStart(3, '0')}-0000-0000-0000-000000000000`,
      name: d.name,
      type: d.type,
      status,
      temperature: randomInRange(rng, ranges.temperature.min, ranges.temperature.max),
      temperature_unit: '°C',
      temperature_range: ranges.temperature,
      pressure: randomInRange(rng, ranges.pressure.min, ranges.pressure.max),
      pressure_unit: 'bar',
      pressure_range: ranges.pressure,
      power: randomInRange(rng, ranges.power_consumption.min, ranges.power_consumption.max),
      power_unit: 'kW',
      power_range: ranges.power_consumption,
      production: randomInRange(rng, ranges.production_output.min, ranges.production_output.max),
      production_unit: 'units/hr',
      production_range: ranges.production_output,
    };
  });
}

const alphaAssets = makeAssets(
  [
    { name: 'Turbine A', type: 'turbine' },
    { name: 'Turbine B', type: 'turbine' },
    { name: 'Boiler #1', type: 'boiler' },
    { name: 'Generator G1', type: 'generator' },
    { name: 'Cooling Tower CT1', type: 'cooling_tower' },
  ],
  1,
);

const betaAssets = makeAssets(
  [
    { name: 'Reactor R1', type: 'reactor' },
    { name: 'Reactor R2', type: 'reactor' },
    { name: 'Compressor C1', type: 'compressor' },
    { name: 'Distillation Column D1', type: 'distillation_column' },
    { name: 'Heat Exchanger HX1', type: 'heat_exchanger' },
    { name: 'Pump P1', type: 'pump' },
  ],
  2,
);

const gammaAssets = makeAssets(
  [
    { name: 'CNC Machine M1', type: 'cnc_machine' },
    { name: 'CNC Machine M2', type: 'cnc_machine' },
    { name: 'Assembly Robot AR1', type: 'robot' },
    { name: 'Conveyor Belt CB1', type: 'conveyor' },
    { name: 'Furnace F1', type: 'furnace' },
  ],
  3,
);

export { ASSET_TYPE_RANGES };

/* ── Helper: derive KPIs from asset list ── */

function deriveKpis(assets: AssetStatus[]): MetricKPI[] {
  function metricKpi(
    name: string,
    values: number[],
    unit: string,
  ): MetricKPI {
    const sorted = [...values].sort((a, b) => a - b);
    const sum = sorted.reduce((a, b) => a + b, 0);
    const avg = sum / sorted.length;
    const p = (pct: number) => sorted[Math.floor(pct / 100 * (sorted.length - 1))];
    return {
      metric_name: name,
      current_value: Math.round(sum * 100) / 100,
      avg_value: Math.round(avg * 100) / 100,
      min_value: sorted[0],
      max_value: sorted[sorted.length - 1],
      p50_value: Math.round(p(50) * 100) / 100,
      p90_value: Math.round(p(90) * 100) / 100,
      p95_value: Math.round(p(95) * 100) / 100,
      unit,
    };
  }

  const powerVals = assets.map((a) => a.power ?? 0);
  const prodVals = assets.map((a) => a.production ?? 0);

  const powerKpi = metricKpi('power_consumption', powerVals, 'kW');
  const prodKpi = metricKpi('production_output', prodVals, 'units/hr');

  // Efficiency = total_production / total_power
  const totalPower = powerVals.reduce((a, b) => a + b, 0);
  const totalProd = prodVals.reduce((a, b) => a + b, 0);
  const eff = totalPower > 0 ? totalProd / totalPower : 0;

  const efficiencyKpi: MetricKPI = {
    metric_name: 'efficiency',
    current_value: Math.round(eff * 100) / 100,
    avg_value: Math.round(eff * 100) / 100,
    min_value: Math.round(eff * 0.85 * 100) / 100,
    max_value: Math.round(eff * 1.15 * 100) / 100,
    p50_value: Math.round(eff * 100) / 100,
    p90_value: Math.round(eff * 1.1 * 100) / 100,
    p95_value: Math.round(eff * 1.12 * 100) / 100,
    unit: 'units/kW',
  };

  return [powerKpi, prodKpi, efficiencyKpi];
}

/* ── Insights ── */

const alphaInsights: InsightItem[] = [
  {
    severity: 'medium',
    title: 'Turbine B temperature trending high',
    description:
      'Turbine B has been running 8% above normal average temperature over the last 6 hours. Consider scheduling preventive maintenance.',
    detected_at: new Date(Date.now() - 2 * 3600_000).toISOString(),
    asset_name: 'Turbine B',
  },
  {
    severity: 'ok',
    title: 'All generators within normal parameters',
    description:
      'Generator G1 and related systems are operating within expected ranges across all metrics.',
    detected_at: new Date(Date.now() - 12 * 3600_000).toISOString(),
  },
];

const betaInsights: InsightItem[] = [
  {
    severity: 'high',
    title: 'Reactor R2 pressure above threshold',
    description:
      'Reactor R2 pressure has exceeded the 90th-percentile threshold (9.2 bar). Immediate review recommended.',
    detected_at: new Date(Date.now() - 1 * 3600_000).toISOString(),
    asset_name: 'Reactor R2',
  },
  {
    severity: 'low',
    title: 'Pump P1 power consumption slightly elevated',
    description:
      'Pump P1 is consuming 12% more power than its 30-day average. Monitor for further increase.',
    detected_at: new Date(Date.now() - 5 * 3600_000).toISOString(),
    asset_name: 'Pump P1',
  },
  {
    severity: 'ok',
    title: 'Heat Exchanger HX1 efficiency stable',
    description:
      'Heat Exchanger HX1 is maintaining steady operational efficiency within expected parameters.',
    detected_at: new Date(Date.now() - 18 * 3600_000).toISOString(),
  },
];

const gammaInsights: InsightItem[] = [
  {
    severity: 'medium',
    title: 'Furnace F1 temperature fluctuations detected',
    description:
      'Furnace F1 has shown ±15°C fluctuations in the last 4 hours. This may indicate a sensor drift or control loop issue.',
    detected_at: new Date(Date.now() - 3 * 3600_000).toISOString(),
    asset_name: 'Furnace F1',
  },
  {
    severity: 'ok',
    title: 'CNC machines operating normally',
    description:
      'Both CNC Machine M1 and M2 are within operational ranges with stable power consumption.',
    detected_at: new Date(Date.now() - 8 * 3600_000).toISOString(),
  },
];

/* ── Build summary per facility ── */

function buildSummary(
  facilityId: string,
  facilityName: string,
  location: string,
  facilityType: string,
  assets: AssetStatus[],
  insights: InsightItem[],
  periodHours: number = 24,
): FacilitySummaryResponse {
  const operational = assets.filter((a) => a.status === 'operational').length;
  const maintenance = assets.filter((a) => a.status === 'maintenance').length;
  const alertCount = insights.filter(
    (i) => i.severity === 'high' || i.severity === 'medium',
  ).length;

  return {
    facility_id: facilityId,
    facility_name: facilityName,
    location,
    facility_type: facilityType,
    total_assets: assets.length,
    operational_count: operational,
    maintenance_count: maintenance,
    active_alerts_count: alertCount,
    kpis: deriveKpis(assets),
    insights,
    assets,
    period_hours: periodHours,
  };
}

/* ── Exported summaries keyed by facility ID ── */

export const summaries: Record<string, FacilitySummaryResponse> = {
  [FACILITY_IDS.alpha]: buildSummary(
    FACILITY_IDS.alpha,
    'Power Station Alpha',
    'Houston, TX',
    'power_station',
    alphaAssets,
    alphaInsights,
  ),
  [FACILITY_IDS.beta]: buildSummary(
    FACILITY_IDS.beta,
    'Chemical Plant Beta',
    'Rotterdam, NL',
    'chemical_plant',
    betaAssets,
    betaInsights,
  ),
  [FACILITY_IDS.gamma]: buildSummary(
    FACILITY_IDS.gamma,
    'Manufacturing Gamma',
    'São Paulo, BR',
    'manufacturing',
    gammaAssets,
    gammaInsights,
  ),
};
