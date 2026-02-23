import { Select, Typography } from 'antd';
import { EnvironmentOutlined } from '@ant-design/icons';
import { useFacility } from '../../context/FacilityContext';

const { Text } = Typography;

/**
 * Facility selector shown in the header.
 * Uses className for header-specific styling (translucent bg on dark header)
 * and classNames.popup so the dropdown renders with card-like bg.
 */
export default function FacilitySelector() {
  const { facilities, loading, selectedId, setSelectedId } = useFacility();

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <EnvironmentOutlined style={{ fontSize: 16, color: '#ffbc39', flexShrink: 0 }} />
      <Select
        className="header-facility-select"
        classNames={{ popup: 'header-facility-dropdown' }}
        value={selectedId ?? undefined}
        onChange={setSelectedId}
        loading={loading}
        style={{ minWidth: 240, maxWidth: 300 }}
        placeholder="Select a facility..."
        popupMatchSelectWidth={340}
        getPopupContainer={() => document.body}  /* escape any overflow:hidden */
        options={facilities.map((f) => ({
          value: f.id,
          label: f.name,
          searchLabel: `${f.name} ${f.location}`,
        }))}
        optionRender={(option) => {
          const fac = facilities.find((f) => f.id === option.value);
          return (
            <div style={{ padding: '4px 0' }}>
              <Text
                strong
                style={{
                  fontFamily: "'Bai Jamjuree', Arial, sans-serif",
                  display: 'block',
                  color: 'var(--cv-text-primary)',
                }}
              >
                {fac?.name}
              </Text>
              <Text style={{ fontSize: 12, color: 'var(--cv-text-secondary)' }}>
                {fac?.location} &middot; {fac?.asset_count} assets
              </Text>
            </div>
          );
        }}
        listHeight={300}
      />
    </div>
  );
}
