import { useEffect, useState } from 'react';
import { Card, Empty, Select, Skeleton, Space, Segmented } from 'antd';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import dayjs from 'dayjs';

import { useFacility } from '../../context/FacilityContext';
import { fetchTimeseries } from '../../services/api';
import type {
  MetricName,
  TimeseriesResponse,
} from '../../types';
import { METRIC_LABELS, METRIC_UNITS } from '../../types';

// CVector-inspired palette for multi-asset lines
const ASSET_COLORS = [
  '#f55330',  // Flamingo
  '#800139',  // Siren
  '#ffbc39',  // Sunglow
  '#3f8600',  // green
  '#0c0402',  // Neutral darkest
  '#b6b3b3',  // Neutral light
  '#d9442a',  // Flamingo dark
  '#a3014d',  // Siren light
];

/** Flatten TimeseriesResponse into a flat array for Recharts. */
function flattenSeries(ts: TimeseriesResponse) {
  // Collect all unique timestamps
  const map = new Map<string, Record<string, number | string>>();

  for (const s of ts.series) {
    for (const pt of s.data) {
      const key = pt.timestamp;
      if (!map.has(key)) {
        map.set(key, { timestamp: key });
      }
      map.get(key)![s.asset_name] = pt.value;
    }
  }

  return Array.from(map.values()).sort((a, b) =>
    (a.timestamp as string).localeCompare(b.timestamp as string),
  );
}

export default function TimeseriesChart() {
  const { selectedId } = useFacility();
  const [metric, setMetric] = useState<MetricName>('temperature');
  const [hours, setHours] = useState<number>(24);
  const [bucket, setBucket] = useState<number>(5);
  const [data, setData] = useState<TimeseriesResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    fetchTimeseries(selectedId, metric, hours, bucket)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedId, metric, hours, bucket]);

  if (!selectedId) return <Empty description="Select a facility" />;

  const chartData = data ? flattenSeries(data) : [];
  const assetNames = data?.series.map((s) => s.asset_name) ?? [];

  return (
    <Card
      title={
        <Space wrap>
          <span>Historical Data</span>
          <Select
            value={metric}
            onChange={(v) => setMetric(v)}
            style={{ width: 180 }}
            options={(
              Object.keys(METRIC_LABELS) as MetricName[]
            ).map((m) => ({
              value: m,
              label: `${METRIC_LABELS[m]} (${METRIC_UNITS[m]})`,
            }))}
          />
          <Select
            value={bucket}
            onChange={(v) => setBucket(v)}
            style={{ width: 110 }}
            options={[
              { value: 1, label: '1 min' },
              { value: 5, label: '5 min' },
              { value: 15, label: '15 min' },
              { value: 30, label: '30 min' },
              { value: 60, label: '1 hour' },
            ]}
          />
        </Space>
      }
      extra={
        <Segmented
          options={[
            { label: '12h', value: 12 },
            { label: '24h', value: 24 },
            { label: '48h', value: 48 },
          ]}
          value={hours}
          onChange={(v) => setHours(v as number)}
        />
      }
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 10 }} />
      ) : chartData.length === 0 ? (
        <Empty description="No data" />
      ) : (
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={(v: string) => dayjs(v).format('HH:mm')}
              interval="preserveStartEnd"
              fontSize={12}
            />
            <YAxis
              unit={` ${data?.unit ?? ''}`}
              fontSize={12}
              domain={['auto', 'auto']}
            />
            <Tooltip
              labelFormatter={(v) =>
                dayjs(String(v)).format('DD/MM HH:mm')
              }
            />
            <Legend />
            {assetNames.map((name, i) => (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                stroke={ASSET_COLORS[i % ASSET_COLORS.length]}
                dot={false}
                strokeWidth={1.5}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
