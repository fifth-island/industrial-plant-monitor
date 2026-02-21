import { useEffect, useState } from 'react';
import {
  Card,
  Col,
  Row,
  Skeleton,
  Statistic,
  Table,
  Tag,
  Empty,
  Segmented,
} from 'antd';
import {
  ThunderboltOutlined,
  DashboardOutlined,
  FireOutlined,
  RiseOutlined,
  CheckCircleOutlined,
  ToolOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

import { useFacility } from '../../context/FacilityContext';
import { fetchSummary } from '../../services/api';
import type {
  AssetStatus,
  FacilitySummaryResponse,
  MetricName,
} from '../../types';

const METRIC_ICONS: Record<MetricName, React.ReactNode> = {
  temperature: <FireOutlined />,
  pressure: <DashboardOutlined />,
  power_consumption: <ThunderboltOutlined />,
  production_output: <RiseOutlined />,
};

const METRIC_LABEL: Record<MetricName, string> = {
  temperature: 'Avg Temperature',
  pressure: 'Avg Pressure',
  power_consumption: 'Avg Power',
  production_output: 'Avg Production',
};

const METRIC_SUFFIX: Record<MetricName, string> = {
  temperature: '°C',
  pressure: 'bar',
  power_consumption: 'kW',
  production_output: 'units/hr',
};

// Danger thresholds — values above these turn red
const METRIC_THRESHOLDS: Record<MetricName, { warn: number; danger: number }> = {
  temperature:      { warn: 90,  danger: 110 },
  pressure:         { warn: 7,   danger: 9 },
  power_consumption:{ warn: 400, danger: 470 },
  production_output:{ warn: 180, danger: 195 },
};

/** Return a color based on how close the value is to danger. */
function getStatusColor(metric: MetricName, value: number): string {
  const t = METRIC_THRESHOLDS[metric];
  if (value >= t.danger) return '#cf1322';   // red
  if (value >= t.warn)   return '#fa8c16';   // orange
  return '#3f8600';                          // green
}

/** Return an appropriate icon when a metric is in danger zone. */
function getStatusIcon(metric: MetricName, value: number): React.ReactNode {
  const t = METRIC_THRESHOLDS[metric];
  if (value >= t.danger) return <WarningOutlined style={{ color: '#cf1322' }} />;
  if (value >= t.warn)   return <WarningOutlined style={{ color: '#fa8c16' }} />;
  return METRIC_ICONS[metric];
}

const assetColumns: ColumnsType<AssetStatus> = [
  { title: 'Asset', dataIndex: 'name', key: 'name' },
  { title: 'Type', dataIndex: 'type', key: 'type' },
  {
    title: 'Status',
    dataIndex: 'status',
    key: 'status',
    render: (s: string) =>
      s === 'operational' ? (
        <Tag icon={<CheckCircleOutlined />} color="success">
          Operational
        </Tag>
      ) : (
        <Tag icon={<ToolOutlined />} color="warning">
          Maintenance
        </Tag>
      ),
  },
];

export default function KpiCards() {
  const { selectedId } = useFacility();
  const [summary, setSummary] = useState<FacilitySummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [hours, setHours] = useState<number>(24);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    fetchSummary(selectedId, hours)
      .then(setSummary)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedId, hours]);

  if (!selectedId) return <Empty description="Select a facility" />;

  if (loading) {
    return (
      <div>
        <Row gutter={[16, 16]}>
          {[1, 2, 3, 4].map((i) => (
            <Col xs={24} sm={12} lg={6} key={i}>
              <Card>
                <Skeleton active paragraph={{ rows: 2 }} />
              </Card>
            </Col>
          ))}
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
          <Col xs={24} lg={8}>
            <Card><Skeleton active paragraph={{ rows: 2 }} /></Card>
          </Col>
          <Col xs={24} lg={16}>
            <Card><Skeleton active paragraph={{ rows: 4 }} /></Card>
          </Col>
        </Row>
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div>
      {/* Period selector */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Segmented
          options={[
            { label: '12h', value: 12 },
            { label: '24h', value: 24 },
            { label: '48h', value: 48 },
          ]}
          value={hours}
          onChange={(v) => setHours(v as number)}
        />
      </div>

      {/* KPI cards */}
      <Row gutter={[16, 16]}>
        {summary.kpis.map((kpi) => {
          const key = kpi.metric_name as MetricName;
          const color = getStatusColor(key, kpi.current_value);
          return (
            <Col xs={24} sm={12} lg={6} key={key}>
              <Card hoverable>
                <Statistic
                  title={METRIC_LABEL[key]}
                  value={kpi.avg_value}
                  precision={1}
                  prefix={getStatusIcon(key, kpi.current_value)}
                  suffix={METRIC_SUFFIX[key]}
                  valueStyle={{ color }}
                />
                <div
                  style={{
                    marginTop: 8,
                    fontSize: 12,
                    color: 'rgba(0,0,0,0.45)',
                  }}
                >
                  Current:{' '}
                  <span style={{ color, fontWeight: 600 }}>{kpi.current_value}</span>
                  {' '}&middot; Min: {kpi.min_value} &middot; Max: {kpi.max_value}
                </div>
              </Card>
            </Col>
          );
        })}
      </Row>

      {/* Assets overview */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={8}>
          <Card title="Assets Overview">
            <Row gutter={16}>
              <Col span={8}>
                <Statistic title="Total" value={summary.total_assets} />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Online"
                  value={summary.operational_count}
                  valueStyle={{ color: '#3f8600' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Maintenance"
                  value={summary.maintenance_count}
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card title="Asset Status">
            <Table
              columns={assetColumns}
              dataSource={summary.assets}
              rowKey="id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
