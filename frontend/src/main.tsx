import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

// Minimal reset — Ant Design handles theming
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
