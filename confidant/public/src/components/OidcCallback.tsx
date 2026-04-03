import { useContext, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthConfigContext } from '../authConfig.context';

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
      .then(() => {
        navigate('/', { replace: true });
      })
      .catch(() => {
        navigate('/', { replace: true });
      });
  }, [navigate, userManager]);

  return null;
}
