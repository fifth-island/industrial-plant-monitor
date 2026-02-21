import { Layout, Typography } from 'antd';
import {
  DashboardOutlined,
  MoonOutlined,
  SunOutlined,
} from '@ant-design/icons';
import FacilitySelector from '../components/FacilitySelector';
import { useTheme } from '../context/ThemeContext';

const { Header, Content, Footer } = Layout;

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { isDark, toggle } = useTheme();

  return (
    <Layout style={{ minHeight: '100vh', background: 'var(--cv-bg-page)' }}>
      {/* ── Sticky header ── 100% width, Siren gradient ── */}
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          background: 'var(--cv-header-bg)',
          borderBottom: 'none',
          position: 'sticky',
          top: 0,
          zIndex: 100,
          width: '100%',
          height: 56,
          lineHeight: '56px',
          boxShadow: 'var(--cv-header-shadow)',
          overflow: 'visible',   /* allow dropdown popup to escape */
        }}
      >
        {/* Left: branding */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
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
              whiteSpace: 'nowrap',
            }}
          >
            Plant Monitor
          </Typography.Title>
        </div>

        {/* Right: facility selector + theme toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
          <FacilitySelector />
          <button
            className="theme-toggle-btn"
            onClick={toggle}
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            title={isDark ? 'Light mode' : 'Dark mode'}
          >
            {isDark ? <SunOutlined /> : <MoonOutlined />}
          </button>
        </div>
      </Header>

      {/* ── Content ── */}
      <Content style={{ padding: '28px 24px', background: 'var(--cv-bg-page)', transition: 'background 0.3s' }}>
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
          background: 'var(--cv-bg-page)',
          color: 'var(--cv-text-secondary)',
          fontFamily: "'Manrope', Arial, sans-serif",
          fontSize: 13,
          borderTop: '1px solid var(--cv-border-soft)',
          transition: 'background 0.3s, color 0.3s',
        }}
      >
        Plant Monitor Dashboard &copy; 2026
      </Footer>
    </Layout>
  );
}
