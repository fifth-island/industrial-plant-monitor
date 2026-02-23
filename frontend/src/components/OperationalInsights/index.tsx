import { useState } from 'react';
import { Card, List, Tag, Segmented } from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import type { InsightItem } from '../../types';

interface OperationalInsightsProps {
  insights: InsightItem[];
}

type SeverityFilter = 'all' | 'low' | 'medium' | 'high';

const SEVERITY_CONFIG = {
  ok: {
    color: '#3f8600',
    icon: <CheckCircleOutlined />,
    tagColor: 'success',
  },
  low: {
    color: '#1890ff',
    icon: <ExclamationCircleOutlined />,
    tagColor: 'processing',
  },
  medium: {
    color: '#ffbc39',
    icon: <WarningOutlined />,
    tagColor: 'warning',
  },
  high: {
    color: '#f55330',
    icon: <CloseCircleOutlined />,
    tagColor: 'error',
  },
};

export default function OperationalInsights({ insights }: OperationalInsightsProps) {
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all');
  
  const filteredInsights = insights.filter(insight => {
    if (severityFilter === 'all') return true;
    return insight.severity === severityFilter;
  });
  
  return (
    <Card 
      title="Operational Insights"
      extra={
        <Segmented
          size="small"
          options={[
            { label: 'All', value: 'all' },
            { label: 'High', value: 'high' },
            { label: 'Medium', value: 'medium' },
            { label: 'Low', value: 'low' },
          ]}
          value={severityFilter}
          onChange={(value) => setSeverityFilter(value as SeverityFilter)}
        />
      }
    >
      <div style={{ maxHeight: '140px', overflowY: 'auto' }}>
        <List
          size="small"
          dataSource={filteredInsights}
          renderItem={(insight) => {
            const config = SEVERITY_CONFIG[insight.severity];
            const detectedTime = new Date(insight.detected_at).toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
              hour12: false,
            });
            return (
              <List.Item>
                <List.Item.Meta
                  avatar={
                    <span style={{ fontSize: 20, color: config.color }}>
                      {config.icon}
                    </span>
                  }
                  title={
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontWeight: 500 }}>{insight.title}</span>
                      {insight.asset_name && (
                        <Tag style={{ fontSize: 10, background: 'var(--cv-bg-secondary)' }}>
                          {insight.asset_name}
                        </Tag>
                      )}
                      <Tag color={config.tagColor} style={{ textTransform: 'uppercase', fontSize: 10 }}>
                        {insight.severity}
                      </Tag>
                      <span style={{ color: 'var(--cv-text-secondary)', fontSize: 11, marginLeft: 'auto' }}>
                        {detectedTime}
                      </span>
                    </div>
                  }
                  description={
                    <span style={{ color: 'var(--cv-text-secondary)', fontSize: 13 }}>
                      {insight.description}
                    </span>
                  }
                />
              </List.Item>
            );
          }}
        />
      </div>
    </Card>
  );
}
