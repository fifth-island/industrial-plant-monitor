import { ConfigProvider, theme as antTheme } from 'antd';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import { FacilityProvider } from './context/FacilityContext';
import AppLayout from './layout/AppLayout';
import DashboardPage from './pages/DashboardPage';

/**
 * CVector design-system tokens applied to Ant Design.
 * Supports light / dark mode via ThemeContext.
 */
function ThemedApp() {
  const { isDark } = useTheme();

  /* ── Light tokens ── */
  const lightTokens = {
    colorPrimary: '#800139',
    colorInfo: '#800139',
    colorSuccess: '#3f8600',
    colorWarning: '#ffbc39',
    colorError: '#f55330',
    colorLink: '#f55330',
    borderRadius: 10,
    fontFamily: "'Manrope', Arial, sans-serif",
    colorBgContainer: '#fff',
    colorBgLayout: '#faf8f5',
    colorText: '#0c0402',
    colorTextSecondary: '#b6b3b3',
    colorBorder: '#dad9d9',
    colorBorderSecondary: '#e8e1d7',
  };

  /* ── Dark tokens ── */
  const darkTokens = {
    ...lightTokens,
    colorBgContainer: '#1e1b24',
    colorBgLayout: '#141218',
    colorBgElevated: '#262330',
    colorText: '#eae6f0',
    colorTextSecondary: '#8b8594',
    colorBorder: '#33303c',
    colorBorderSecondary: '#2a2733',
  };

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm,
        token: isDark ? darkTokens : lightTokens,
        components: {
          Button: {
            colorPrimary: '#f55330',
            colorPrimaryHover: '#d9442a',
            borderRadius: 8,
            fontWeight: 500,
          },
          Card: {
            borderRadiusLG: 12,
          },
          Select: {
            borderRadius: 8,
          },
          Table: {
            headerBg: isDark ? '#1e1b24' : '#faf8f5',
            headerColor: isDark ? '#eae6f0' : '#0c0402',
          },
        },
      }}
    >
      <FacilityProvider>
        <AppLayout>
          <DashboardPage />
        </AppLayout>
      </FacilityProvider>
    </ConfigProvider>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <ThemedApp />
    </ThemeProvider>
  );
}
