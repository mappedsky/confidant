import React, { useMemo, useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { createAppTheme } from './theme';
import AuthProvider from './components/AuthProvider';
import OidcCallback from './components/OidcCallback';
import { AppProvider } from './contexts/AppContext';
import { AuthConfigContext, type AuthConfig } from './authConfig.context';
import Layout from './components/Layout';
import { AuthConfigResponse, OidcConfig } from './types/api';
import { createUserManager } from './userManager';
import CredentialListPage from './pages/CredentialListPage';
import CredentialDetailPage from './pages/CredentialDetailPage';
import CredentialHistoryPage from './pages/CredentialHistoryPage';
import ServiceListPage from './pages/ServiceListPage';
import ServiceDetailPage from './pages/ServiceDetailPage';
import ServiceHistoryPage from './pages/ServiceHistoryPage';

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
  const [authConfigReady, setAuthConfigReady] = useState(false);
  const [authConfig, setAuthConfig] = useState<AuthConfig>({
    auth_required: true,
    oidc: null,
    userManager: null,
  });

  useEffect(() => {
    fetch('/v1/auth_config')
      .then((res) => res.json())
      .then((data: AuthConfigResponse) => {
        const oidc = data.oidc ?? null;
        const userManager = data.auth_required && oidc ? createUserManager(oidc) : null;
        setAuthConfig({
          auth_required: data.auth_required,
          oidc: oidc as OidcConfig | null,
          userManager,
        });
        setAuthConfigReady(true);
      })
      .catch(() => {
        // Keep the safe default on load failure.
        setAuthConfigReady(true);
      });
  }, []);

  if (!authConfigReady) {
    return null;
  }

  return (
    <AuthConfigContext.Provider value={authConfig}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>
          <AuthProvider>
            <Routes>
              <Route path="/auth/callback" element={<OidcCallback />} />
              <Route
                path="*"
                element={(
                  <AppProvider>
                    <Layout>
                      <Routes>
                        <Route path="/" element={<Navigate to="/credentials" replace />} />
                        <Route path="/credentials" element={<CredentialListPage />} />
                        <Route path="/credentials/new" element={<CredentialDetailPage />} />
                        <Route path="/credentials/:id/history" element={<CredentialHistoryPage />} />
                        <Route path="/credentials/:id/versions/:version" element={<CredentialDetailPage />} />
                        <Route path="/credentials/:id" element={<CredentialDetailPage />} />
                        <Route path="/services" element={<ServiceListPage />} />
                        <Route path="/services/new" element={<ServiceDetailPage />} />
                        <Route path="/services/:id/history" element={<ServiceHistoryPage />} />
                        <Route path="/services/:id/versions/:version" element={<ServiceDetailPage />} />
                        <Route path="/services/:id" element={<ServiceDetailPage />} />
                        <Route path="*" element={<Navigate to="/credentials" replace />} />
                      </Routes>
                    </Layout>
                  </AppProvider>
                )}
              />
            </Routes>
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </AuthConfigContext.Provider>
  );
}
