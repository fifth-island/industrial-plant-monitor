import React, { createContext, useContext, useEffect, useState } from 'react';
import type { Facility } from '../types';
import { fetchFacilities } from '../services/api';

interface FacilityContextValue {
  facilities: Facility[];
  loading: boolean;
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

  useEffect(() => {
    fetchFacilities()
      .then((res) => {
        setFacilities(res.facilities);
        // Auto-select the first facility
        if (res.facilities.length > 0 && !selectedId) {
          setSelectedId(res.facilities[0].id);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selected = facilities.find((f) => f.id === selectedId);

  return (
    <FacilityContext.Provider
      value={{ facilities, loading, selectedId, setSelectedId, selected }}
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
