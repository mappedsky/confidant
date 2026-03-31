import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, setXsrfCookieName } from '../api';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [clientConfig, setClientConfig] = useState(null);
  const [userEmail, setUserEmail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.getClientConfig(), api.getUserEmail()])
      .then(([config, user]) => {
        if (config.generated?.xsrf_cookie_name) {
          setXsrfCookieName(config.generated.xsrf_cookie_name);
        }
        setClientConfig(config);
        setUserEmail(user.email);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return (
    <AppContext.Provider value={{ clientConfig, userEmail, loading, error }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  return useContext(AppContext);
}
