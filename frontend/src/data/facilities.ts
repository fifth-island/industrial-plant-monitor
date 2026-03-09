import type { Facility, FacilitiesListResponse } from '../types';

/* ── Deterministic facility IDs (stable across reloads) ── */

export const FACILITY_IDS = {
  alpha: 'f0000001-0000-0000-0000-000000000001',
  beta:  'f0000002-0000-0000-0000-000000000002',
  gamma: 'f0000003-0000-0000-0000-000000000003',
} as const;

export const facilities: Facility[] = [
  {
    id: FACILITY_IDS.alpha,
    name: 'Power Station Alpha',
    location: 'Houston, TX',
    type: 'power_station',
    asset_count: 5,
    created_at: '2024-01-15T08:00:00Z',
  },
  {
    id: FACILITY_IDS.beta,
    name: 'Chemical Plant Beta',
    location: 'Rotterdam, NL',
    type: 'chemical_plant',
    asset_count: 6,
    created_at: '2024-02-20T10:00:00Z',
  },
  {
    id: FACILITY_IDS.gamma,
    name: 'Manufacturing Gamma',
    location: 'São Paulo, BR',
    type: 'manufacturing',
    asset_count: 5,
    created_at: '2024-03-10T14:00:00Z',
  },
];

export const facilitiesListResponse: FacilitiesListResponse = {
  facilities,
};
