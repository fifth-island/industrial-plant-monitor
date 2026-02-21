import { ConfigProvider } from 'antd';
import { FacilityProvider } from './context/FacilityContext';
import AppLayout from './layout/AppLayout';
import DashboardPage from './pages/DashboardPage';

/**
 * CVector design-system tokens applied to Ant Design.
 *
 * Palette:
 *   Flamingo #f55330  — primary CTA / accents
 *   Siren    #800139  — deep accent / dark sections
 *   Sunglow  #ffbc39  — secondary accent / badges
 *   Clay     #e8e1d7  — soft backgrounds
 */
export default function App() {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#800139',         // Siren — main interactive color
          colorInfo: '#800139',
          colorSuccess: '#3f8600',
          colorWarning: '#ffbc39',          // Sunglow
          colorError: '#f55330',            // Flamingo
          colorLink: '#f55330',
          borderRadius: 10,
          fontFamily: "'Manrope', Arial, sans-serif",
          colorBgContainer: '#fff',
          colorBgLayout: '#faf8f5',
          colorText: '#0c0402',             // Neutral Darkest
          colorTextSecondary: '#b6b3b3',    // Neutral Light
          colorBorder: '#dad9d9',           // Neutral Lighter
          colorBorderSecondary: '#e8e1d7',  // Clay
        },
        components: {
          Button: {
            colorPrimary: '#f55330',        // Flamingo for CTAs
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
            headerBg: '#faf8f5',
            headerColor: '#0c0402',
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
