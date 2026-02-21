import { Typography } from 'antd';
import { useFacility } from '../context/FacilityContext';
import KpiCards from '../components/KpiCards';
import TimeseriesChart from '../components/TimeseriesChart';

const { Title, Text } = Typography;

export default function DashboardPage() {
  const { selected, loading } = useFacility();

  if (loading) return null;

  return (
    <div>
      {/* Facility header */}
      <div style={{ marginBottom: 24 }}>
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

      <KpiCards />

      <div style={{ marginTop: 28 }}>
        <TimeseriesChart />
      </div>
    </div>
  );
}
