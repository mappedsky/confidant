import { ReactNode, useContext, useEffect, useLayoutEffect, useState } from 'react';
import type { User } from 'oidc-client-ts';
import { useLocation } from 'react-router-dom';
import { AuthContext } from '../auth.context';
import { AuthConfigContext } from '../authConfig.context';
import { setAccessTokenGetter, setUnauthorizedHandler } from '../api';

const UNAUTHENTICATED_PATHS = ['/auth/callback', '/loggedout'];

interface AuthProviderProps {
  children: ReactNode;
}

export default function AuthProvider({ children }: AuthProviderProps) {
  const { auth_required, userManager } = useContext(AuthConfigContext);
  const location = useLocation();
  const isUnauthenticatedPath = UNAUTHENTICATED_PATHS.includes(location.pathname);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(auth_required && userManager !== null);

  useEffect(() => {
    if (!auth_required || !userManager) {
      setIsLoading(false);
      return undefined;
    }

    const onUserLoaded = (loadedUser: User) => {
      setUser(loadedUser);
      setIsLoading(false);
    };
    const onUserUnloaded = () => {
      setUser(null);
    };

    userManager.events.addUserLoaded(onUserLoaded);
    userManager.events.addUserUnloaded(onUserUnloaded);

    if (isUnauthenticatedPath) {
      setIsLoading(false);
    } else {
      setIsLoading(true);
      (async () => {
        const loadedUser = await userManager.getUser();
        if (loadedUser && !loadedUser.expired) {
          setUser(loadedUser);
          setIsLoading(false);
          return;
        }
        userManager.signinRedirect();
      })();
    }

    return () => {
      userManager.events.removeUserLoaded(onUserLoaded);
      userManager.events.removeUserUnloaded(onUserUnloaded);
    };
  }, [auth_required, isUnauthenticatedPath, userManager]);

  const accessToken = user?.access_token ?? null;
  const shouldHoldProtectedRoutes =
    auth_required &&
    userManager !== null &&
    !isUnauthenticatedPath &&
    accessToken === null;

  useLayoutEffect(() => {
    if (!auth_required || !userManager) {
      setAccessTokenGetter(() => null);
      setUnauthorizedHandler(null);
      return;
    }

    setAccessTokenGetter(() => accessToken);
    setUnauthorizedHandler(() => userManager.signinRedirect());

    return () => {
      setAccessTokenGetter(() => null);
      setUnauthorizedHandler(null);
    };
  }, [accessToken, auth_required, userManager]);

  return (
    <AuthContext.Provider value={{ user, accessToken, isLoading }}>
      {isLoading || shouldHoldProtectedRoutes ? null : children}
    </AuthContext.Provider>
  );
}
