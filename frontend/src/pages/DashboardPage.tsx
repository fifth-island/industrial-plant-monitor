import { useState, useCallback, useEffect } from 'react';
import { Typography } from 'antd';
import { ClockCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { useFacility } from '../context/FacilityContext';
import KpiCards from '../components/KpiCards';
import TimeseriesChart from '../components/TimeseriesChart';

const { Title, Text } = Typography;

export default function DashboardPage() {
  const { selected, loading } = useFacility();
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [loadStartTime, setLoadStartTime] = useState<number | null>(null);

  // Track when facility changes to measure load time
  useEffect(() => {
    if (selected) {
      console.log(`[Performance] Loading dashboard for: ${selected.name}`);
      setLoadStartTime(Date.now());
    }
  }, [selected]);

  const handleDataLoaded = useCallback(() => {
    const now = new Date();
    setLastUpdated(now);
    
    // Log load time on first complete load
    if (loadStartTime) {
      const loadTime = Date.now() - loadStartTime;
      console.log(`[Performance] Dashboard loaded in ${loadTime}ms`);
      setLoadStartTime(null);
    }
  }, [loadStartTime]);

  if (loading) return null;

  return (
    <div>
      {/* Facility header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
          <Title
            level={3}
            style={{
              margin: 0,
              fontFamily: "'Bai Jamjuree', Arial, sans-serif",
              fontWeight: 400,
              color: 'var(--cv-text-primary)',
            }}
          >
            {selected?.name ?? 'Dashboard'}
          </Title>
          {lastUpdated && (
            <Text
              style={{
                color: 'var(--cv-text-tertiary)',
                fontSize: 13,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <ClockCircleOutlined />
              Last updated: {dayjs(lastUpdated).format('HH:mm:ss')}
            </Text>
          )}
        </div>
        {selected && (
          <Text
            style={{
              color: 'var(--cv-text-secondary)',
              fontSize: 14,
              textTransform: 'capitalize',
            }}
          >
            {selected.location} &middot; {selected.type.replace('_', ' ')}
          </Text>
        )}
      </div>

      <KpiCards onDataLoaded={handleDataLoaded} />

      <div style={{ marginTop: 28 }}>
        <TimeseriesChart onDataLoaded={handleDataLoaded} />
      </div>
    </div>
  );
}
