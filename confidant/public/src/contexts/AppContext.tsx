import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from 'react';
import { api, setXsrfCookieName } from '../api';
import { ClientConfigResponse } from '../types/api';
import { AuthContext } from '../auth.context';
import { AuthConfigContext } from '../authConfig.context';

interface AppContextValue {
  clientConfig: ClientConfigResponse | null;
  userEmail: string | null;
  loading: boolean;
  error: string | null;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);

interface AppProviderProps {
  children: ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
  const { accessToken, isLoading: authLoading } = useContext(AuthContext);
  const { auth_required } = useContext(AuthConfigContext);
  const [clientConfig, setClientConfig] = useState<ClientConfigResponse | null>(
    null,
  );
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (auth_required && (authLoading || !accessToken)) {
      setLoading(true);
      return;
    }

    setError(null);
    Promise.all([api.getClientConfig(), api.getUserEmail()])
      .then(([config, user]) => {
        if (config.generated?.xsrf_cookie_name) {
          setXsrfCookieName(config.generated.xsrf_cookie_name);
        }
        setClientConfig(config);
        setUserEmail(user.email);
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
      });
  }, [accessToken, authLoading, auth_required]);

  return (
    <AppContext.Provider value={{ clientConfig, userEmail, loading, error }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext(): AppContextValue {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('AppContext must be used within AppProvider');
  }
  return context;
}
