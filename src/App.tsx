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
import SecretListPage from './pages/SecretListPage';
import SecretDetailPage from './pages/SecretDetailPage';
import SecretHistoryPage from './pages/SecretHistoryPage';
import GroupListPage from './pages/GroupListPage';
import GroupDetailPage from './pages/GroupDetailPage';
import GroupHistoryPage from './pages/GroupHistoryPage';
import SecretRouteResolver from './components/SecretRouteResolver';

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
                        <Route path="/" element={<Navigate to="secrets" replace />} />
                        <Route path="secrets" element={<SecretListPage />} />
                        <Route path="secrets/new" element={<SecretDetailPage />} />
                        <Route path="secrets/view" element={<SecretDetailPage />} />
                        <Route path="secrets/history" element={<SecretHistoryPage />} />
                        <Route path="secrets/version" element={<SecretDetailPage />} />
                        <Route path="secrets/*" element={<SecretRouteResolver />} />
                        <Route path="groups" element={<GroupListPage />} />
                        <Route path="groups/new" element={<GroupDetailPage />} />
                        <Route path="groups/:id/history" element={<GroupHistoryPage />} />
                        <Route path="groups/:id/versions/:version" element={<GroupDetailPage />} />
                        <Route path="groups/:id" element={<GroupDetailPage />} />
                        <Route path="*" element={<Navigate to="secrets" replace />} />
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
