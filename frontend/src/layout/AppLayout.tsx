import { Layout, Typography, theme } from 'antd';
import {
  DashboardOutlined,
} from '@ant-design/icons';
import FacilitySelector from '../components/FacilitySelector';

const { Header, Content, Footer } = Layout;

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* Sticky header */}
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          background: colorBgContainer,
          borderBottom: '1px solid #f0f0f0',
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <DashboardOutlined style={{ fontSize: 22, color: '#1890ff' }} />
          <Typography.Title level={4} style={{ margin: 0 }}>
            Plant Monitor
          </Typography.Title>
        </div>
        <FacilitySelector />
      </Header>

      {/* Content */}
      <Content style={{ padding: '24px', background: '#f5f5f5' }}>
        <div
          style={{
            maxWidth: 1400,
            margin: '0 auto',
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            padding: 24,
            minHeight: 'calc(100vh - 134px)',
          }}
        >
          {children}
        </div>
      </Content>

      <Footer style={{ textAlign: 'center', padding: '12px 50px' }}>
        Plant Monitor Dashboard &copy; 2026
      </Footer>
    </Layout>
  );
}
