import React, { useMemo, useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { createAppTheme } from './theme';
import { AppProvider } from './contexts/AppContext';
import Layout from './components/Layout';
import CredentialListPage from './pages/CredentialListPage';
import CredentialDetailPage from './pages/CredentialDetailPage';
import ServiceListPage from './pages/ServiceListPage';
import ServiceDetailPage from './pages/ServiceDetailPage';

type ColorScheme = 'light' | 'dark';

function useSystemColorMode(): ColorScheme {
  const [mode, setMode] = useState<ColorScheme>(() =>
    window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
  );

  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) =>
      setMode(e.matches ? 'dark' : 'light');
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  return mode;
}

export default function App() {
  const mode = useSystemColorMode();
  const theme = useMemo(() => createAppTheme(mode), [mode]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AppProvider>
          <Layout>
            <Routes>
              <Route path="/" element={<Navigate to="/credentials" replace />} />
              <Route path="/credentials" element={<CredentialListPage />} />
              <Route path="/credentials/new" element={<CredentialDetailPage />} />
              <Route path="/credentials/:id" element={<CredentialDetailPage />} />
              <Route path="/services" element={<ServiceListPage />} />
              <Route path="/services/new" element={<ServiceDetailPage />} />
              <Route path="/services/:id" element={<ServiceDetailPage />} />
              <Route path="*" element={<Navigate to="/credentials" replace />} />
            </Routes>
          </Layout>
        </AppProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}
