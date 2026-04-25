import { useContext, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import type { User } from 'oidc-client-ts';
import { AuthConfigContext } from '../authConfig.context';

function getReturnTo(user: User | undefined): string {
  const returnTo = (user?.state as { returnTo?: unknown } | undefined)?.returnTo;
  return typeof returnTo === 'string' && returnTo.startsWith('/')
    ? returnTo
    : '/';
}

export default function OidcCallback() {
  const navigate = useNavigate();
  const { userManager } = useContext(AuthConfigContext);
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current || !userManager) {
      return;
    }
    handled.current = true;

    userManager
      .signinRedirectCallback()
      .then((user) => {
        navigate(getReturnTo(user), { replace: true });
      })
      .catch(() => {
        navigate('/', { replace: true });
      });
  }, [navigate, userManager]);

  return null;
}
