import { Select, Space, Typography } from 'antd';
import { EnvironmentOutlined } from '@ant-design/icons';
import { useFacility } from '../../context/FacilityContext';

const { Text } = Typography;

/** Dropdown to select the active facility. */
export default function FacilitySelector() {
  const { facilities, loading, selectedId, setSelectedId } = useFacility();

  return (
    <Space>
      <EnvironmentOutlined style={{ fontSize: 18 }} />
      <Select
        value={selectedId ?? undefined}
        onChange={setSelectedId}
        loading={loading}
        style={{ minWidth: 260 }}
        placeholder="Select a facility..."
        options={facilities.map((f) => ({
          value: f.id,
          label: (
            <Space direction="vertical" size={0} style={{ lineHeight: 1.3 }}>
              <Text strong>{f.name}</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {f.location} &middot; {f.asset_count} assets
              </Text>
            </Space>
          ),
        }))}
        optionRender={(option) => option.label}
        listHeight={300}
      />
    </Space>
  );
}
