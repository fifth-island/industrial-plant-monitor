import React, { createContext, useContext, useEffect, useState } from 'react';
import type { Facility } from '../types';
import { fetchFacilities } from '../services/api';

interface FacilityContextValue {
  facilities: Facility[];
  loading: boolean;
  error: string | null;
  selectedId: string | null;
  setSelectedId: (id: string) => void;
  /** Currently selected facility (derived from selectedId). */
  selected: Facility | undefined;
}

const FacilityContext = createContext<FacilityContextValue | null>(null);

export const FacilityProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setError(null);
        const res = await fetchFacilities();
        if (cancelled) return;
        setFacilities(res.facilities);
        if (res.facilities.length > 0 && !selectedId) {
          setSelectedId(res.facilities[0].id);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) setError('Failed to load facilities. The server may be waking up — retrying…');
        // Auto-retry after 5 s (Render cold-start can take 30s+)
        setTimeout(() => { if (!cancelled) load(); }, 5_000);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selected = facilities.find((f) => f.id === selectedId);

  return (
    <FacilityContext.Provider
      value={{ facilities, loading, error, selectedId, setSelectedId, selected }}
    >
      {children}
    </FacilityContext.Provider>
  );
};

export function useFacility(): FacilityContextValue {
  const ctx = useContext(FacilityContext);
  if (!ctx) throw new Error('useFacility must be used inside FacilityProvider');
  return ctx;
}
