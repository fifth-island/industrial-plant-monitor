import { Typography, Divider } from 'antd';
import { useFacility } from '../context/FacilityContext';
import KpiCards from '../components/KpiCards';
import TimeseriesChart from '../components/TimeseriesChart';

const { Title, Text } = Typography;

export default function DashboardPage() {
  const { selected, loading } = useFacility();

  if (loading) return null;

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          {selected?.name ?? 'Dashboard'}
        </Title>
        {selected && (
          <Text type="secondary">
            {selected.location} &middot; {selected.type.replace('_', ' ')}
          </Text>
        )}
      </div>

      <KpiCards />

      <Divider />

      <TimeseriesChart />
    </div>
  );
}
