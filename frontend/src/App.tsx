import { ConfigProvider } from 'antd';
import { FacilityProvider } from './context/FacilityContext';
import AppLayout from './layout/AppLayout';
import DashboardPage from './pages/DashboardPage';

export default function App() {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 6,
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
