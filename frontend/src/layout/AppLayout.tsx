import { Layout, Typography } from 'antd';
import {
  DashboardOutlined,
} from '@ant-design/icons';
import FacilitySelector from '../components/FacilitySelector';

const { Header, Content, Footer } = Layout;

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <Layout style={{ minHeight: '100vh', background: '#faf8f5' }}>
      {/* Sticky header — Siren gradient */}
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 32px',
          background: 'linear-gradient(135deg, #800139 0%, #5a012a 100%)',
          borderBottom: 'none',
          position: 'sticky',
          top: 0,
          zIndex: 10,
          height: 56,
          lineHeight: '56px',
          boxShadow: '0 2px 8px rgba(128,1,57,0.18)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <DashboardOutlined style={{ fontSize: 20, color: '#ffbc39' }} />
          <Typography.Title
            level={4}
            style={{
              margin: 0,
              color: '#fff',
              fontFamily: "'Bai Jamjuree', Arial, sans-serif",
              fontWeight: 400,
              fontSize: 18,
              letterSpacing: 0.5,
            }}
          >
            Plant Monitor
          </Typography.Title>
        </div>
        <FacilitySelector />
      </Header>

      {/* Content */}
      <Content style={{ padding: '28px 24px', background: '#faf8f5' }}>
        <div
          style={{
            maxWidth: 1440,
            margin: '0 auto',
            minHeight: 'calc(100vh - 134px)',
          }}
        >
          {children}
        </div>
      </Content>

      <Footer
        style={{
          textAlign: 'center',
          padding: '14px 50px',
          background: '#faf8f5',
          color: '#b6b3b3',
          fontFamily: "'Manrope', Arial, sans-serif",
          fontSize: 13,
          borderTop: '1px solid #e8e1d7',
        }}
      >
        Plant Monitor Dashboard &copy; 2026
      </Footer>
    </Layout>
  );
}
