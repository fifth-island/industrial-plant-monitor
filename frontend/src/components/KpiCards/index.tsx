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
import { fetchSummary, streamSummary } from '../../services/api';
import OperationalInsights from '../OperationalInsights';
import type {
  AssetStatus,
  FacilitySummaryResponse,
} from '../../types';

/** Format large numbers with abbreviations (K, M, B) */
function formatLargeNumber(value: number): string {
  if (value >= 1_000_000_000) {
    return (value / 1_000_000_000).toFixed(2) + ' bi';
  }
  if (value >= 1_000_000) {
    return (value / 1_000_000).toFixed(2) + ' M';
  }
  if (value >= 1_000) {
    return (value / 1_000).toFixed(2) + ' K';
  }
  return value.toFixed(1);
}

/** Return a CVector-palette color based on value relative to range. */
function getMetricColor(value: number | null | undefined, range: { min: number; max: number } | undefined): string {
  if (value === null || value === undefined || !range) return 'var(--cv-text-secondary)';
  const { min, max } = range;
  const dangerThreshold = max * 0.9; // 90% of max = danger
  const warnThreshold = max * 0.75;  // 75% of max = warning
  
  if (value >= dangerThreshold) return '#f55330';  // Flamingo (danger)
  if (value >= warnThreshold) return '#ffbc39';    // Sunglow (warning)
  return '#3f8600';                                 // Green (ok)
}

const assetColumns: ColumnsType<AssetStatus> = [
  { 
    title: 'Asset', 
    dataIndex: 'name', 
    key: 'name',
    sorter: (a, b) => a.name.localeCompare(b.name),
  },
  { 
    title: 'Type', 
    dataIndex: 'type', 
    key: 'type',
    sorter: (a, b) => a.type.localeCompare(b.type),
  },
  {
    title: 'Status',
    dataIndex: 'status',
    key: 'status',
    sorter: (a, b) => a.status.localeCompare(b.status),
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
  {
    title: <><FireOutlined /> Temp</>,
    dataIndex: 'temperature',
    key: 'temperature',
    sorter: (a, b) => (a.temperature ?? 0) - (b.temperature ?? 0),
    render: (val: number | null, record: AssetStatus) => {
      if (val === null || val === undefined) return '-';
      const color = getMetricColor(val, record.temperature_range);
      return (
        <div>
          <div style={{ color, fontWeight: 600 }}>{val.toFixed(1)}°C</div>
          {record.temperature_range && (
            <div style={{ fontSize: 11, color: 'var(--cv-text-tertiary)' }}>
              {record.temperature_range.min}-{record.temperature_range.max}
            </div>
          )}
        </div>
      );
    },
  },
  {
    title: <><DashboardOutlined /> Pressure</>,
    dataIndex: 'pressure',
    key: 'pressure',
    sorter: (a, b) => (a.pressure ?? 0) - (b.pressure ?? 0),
    render: (val: number | null, record: AssetStatus) => {
      if (val === null || val === undefined) return '-';
      const color = getMetricColor(val, record.pressure_range);
      return (
        <div>
          <div style={{ color, fontWeight: 600 }}>{val.toFixed(1)} bar</div>
          {record.pressure_range && (
            <div style={{ fontSize: 11, color: 'var(--cv-text-tertiary)' }}>
              {record.pressure_range.min}-{record.pressure_range.max}
            </div>
          )}
        </div>
      );
    },
  },
  {
    title: <><ThunderboltOutlined /> Power</>,
    dataIndex: 'power',
    key: 'power',
    sorter: (a, b) => (a.power ?? 0) - (b.power ?? 0),
    render: (val: number | null, record: AssetStatus) => {
      if (val === null || val === undefined) return '-';
      const color = getMetricColor(val, record.power_range);
      return (
        <div>
          <div style={{ color, fontWeight: 600 }}>{val.toFixed(0)} kW</div>
          {record.power_range && (
            <div style={{ fontSize: 11, color: 'var(--cv-text-tertiary)' }}>
              {record.power_range.min}-{record.power_range.max}
            </div>
          )}
        </div>
      );
    },
  },
  {
    title: <><RiseOutlined /> Production</>,
    dataIndex: 'production',
    key: 'production',
    sorter: (a, b) => (a.production ?? 0) - (b.production ?? 0),
    render: (val: number | null, record: AssetStatus) => {
      if (val === null || val === undefined) return '-';
      const color = getMetricColor(val, record.production_range);
      return (
        <div>
          <div style={{ color, fontWeight: 600 }}>{val.toFixed(0)} u/h</div>
          {record.production_range && (
            <div style={{ fontSize: 11, color: 'var(--cv-text-tertiary)' }}>
              {record.production_range.min}-{record.production_range.max}
            </div>
          )}
        </div>
      );
    },
  },
];

interface KpiCardsProps {
  onDataLoaded?: () => void;
}

export default function KpiCards({ onDataLoaded }: KpiCardsProps) {
  const { selectedId } = useFacility();
  const [summary, setSummary] = useState<FacilitySummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [hours, setHours] = useState<number>(24);
  const [usePolling, setUsePolling] = useState(false);
  const [sseErrorCount, setSseErrorCount] = useState(0);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    let retryTimer: ReturnType<typeof setTimeout>;
    let eventSource: EventSource | null = null;
    let refreshTimer: ReturnType<typeof setInterval> | null = null;

    async function initialLoad() {
      if (cancelled) return;
      setLoading(true);
      try {
        const res = await fetchSummary(selectedId!, hours);
        if (!cancelled) {
          setSummary(res);
          onDataLoaded?.();
        }
      } catch (err) {
        console.error(err);
        retryTimer = setTimeout(initialLoad, 4_000);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    // Initial load for fast first render
    initialLoad();

    // Choose between SSE or polling based on fallback state
    if (!usePolling && sseErrorCount < 3) {
      // Use SSE streaming
      eventSource = streamSummary(
        selectedId!,
        hours,
        (data) => {
          if (!cancelled) {
            setSummary(data);
            onDataLoaded?.();
            setSseErrorCount(0); // Reset error count on success
          }
        },
        () => {
          // SSE error handler
          setSseErrorCount((prev) => {
            const newCount = prev + 1;
            console.warn(`[SSE] Error count: ${newCount}/3`);
            if (newCount >= 3) {
              console.warn('[SSE] Max errors reached, falling back to polling');
              setUsePolling(true);
            }
            return newCount;
          });
        }
      );
    } else {
      // Fallback to polling
      console.info('[Polling] Using 30-second interval polling');
      refreshTimer = setInterval(async () => {
        if (cancelled) return;
        try {
          const res = await fetchSummary(selectedId!, hours);
          if (!cancelled) {
            setSummary(res);
            onDataLoaded?.();
          }
        } catch (err) {
          console.error('[Polling] Error:', err);
        }
      }, 30_000);
    }

    return () => {
      cancelled = true;
      clearTimeout(retryTimer);
      if (eventSource) eventSource.close();
      if (refreshTimer) clearInterval(refreshTimer);
    };
  }, [selectedId, hours, onDataLoaded, usePolling, sseErrorCount]);

  if (!selectedId) return <Empty description="Select a facility" />;

  if (loading) {
    return (
      <div>
        <Row gutter={[16, 16]}>
          {[1, 2, 3, 4, 5].map((i) => (
            <Col xs={24} sm={12} md={8} lg={4} xxl={4} key={i}>
              <Card>
                <Skeleton active paragraph={{ rows: 1 }} />
              </Card>
            </Col>
          ))}
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
          <Col xs={24} lg={12}>
            <Card><Skeleton active paragraph={{ rows: 2 }} /></Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card><Skeleton active paragraph={{ rows: 4 }} /></Card>
          </Col>
        </Row>
      </div>
    );
  }

  if (!summary) return null;
  
  // Extract KPI values
  const powerKPI = summary.kpis.find(k => k.metric_name === 'power_consumption');
  const productionKPI = summary.kpis.find(k => k.metric_name === 'production_output');
  const efficiencyKPI = summary.kpis.find(k => k.metric_name === 'efficiency');

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

      {/* 5 KPI cards */}
      <Row gutter={[16, 16]}>
        {/* Total Power Consumption */}
        <Col xs={24} sm={12} md={8} lg={5} xl={5} flex="1">
          <Card hoverable style={{ minHeight: 160 }}>
            <Statistic
              title="Total Power"
              value={formatLargeNumber(powerKPI?.current_value ?? 0)}
              suffix={powerKPI?.unit}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
            <div style={{ fontSize: 12, color: 'var(--cv-text-tertiary)', marginTop: 8 }}>
              Min: {powerKPI?.min_value} | Max: {powerKPI?.max_value}
            </div>
          </Card>
        </Col>
        
        {/* Total Production Output */}
        <Col xs={24} sm={12} md={8} lg={5} xl={5} flex="1">
          <Card hoverable style={{ minHeight: 160 }}>
            <Statistic
              title="Total Production"
              value={formatLargeNumber(productionKPI?.current_value ?? 0)}
              suffix={productionKPI?.unit}
              prefix={<RiseOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
            <div style={{ fontSize: 12, color: 'var(--cv-text-tertiary)', marginTop: 8 }}>
              Min: {productionKPI?.min_value} | Max: {productionKPI?.max_value}
            </div>
          </Card>
        </Col>
        
        {/* System Efficiency */}
        <Col xs={24} sm={12} md={8} lg={5} xl={5} flex="1">
          <Card hoverable style={{ minHeight: 160 }}>
            <Statistic
              title="Efficiency"
              value={efficiencyKPI?.current_value ?? 0}
              precision={2}
              suffix={efficiencyKPI?.unit}
              prefix={<DashboardOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
            <div style={{ fontSize: 12, color: 'var(--cv-text-tertiary)', marginTop: 8 }}>
              units per kW
            </div>
          </Card>
        </Col>
        
        {/* Active Alerts */}
        <Col xs={24} sm={12} md={8} lg={5} xl={5} flex="1">
          <Card hoverable style={{ minHeight: 160 }}>
            <Statistic
              title="Active Alerts"
              value={summary.active_alerts_count}
              prefix={<WarningOutlined />}
              valueStyle={{ 
                color: summary.active_alerts_count > 0 ? '#ff4d4f' : '#52c41a' 
              }}
            />
            <div style={{ fontSize: 12, color: 'var(--cv-text-tertiary)', marginTop: 8 }}>
              high/medium severity
            </div>
          </Card>
        </Col>
        
        {/* Assets Overview */}
        <Col xs={24} sm={12} md={8} lg={5} xl={5} flex="1">
          <Card hoverable style={{ minHeight: 160 }}>
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 14, color: 'var(--cv-text-secondary)' }}>
                Assets Overview
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 12 }}>Total:</span>
              <span style={{ fontSize: 16, fontWeight: 600 }}>{summary.total_assets}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 12, color: '#52c41a' }}>Online:</span>
              <span style={{ fontSize: 14, fontWeight: 500, color: '#52c41a' }}>
                {summary.operational_count}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 12, color: '#faad14' }}>Maintenance:</span>
              <span style={{ fontSize: 14, fontWeight: 500, color: '#faad14' }}>
                {summary.maintenance_count}
              </span>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Two-column layout: Operational Insights + Asset Status table */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={8}>
          <OperationalInsights insights={summary.insights} />
        </Col>
        <Col xs={24} lg={16}>
          <Card title="Asset Status" style={{ height: '100%' }}>
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
