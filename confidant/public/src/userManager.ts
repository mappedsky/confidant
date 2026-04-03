import { UserManager, type UserManagerSettings } from 'oidc-client-ts';
import type { OidcConfig } from './types/api';

export function createUserManager(config: OidcConfig): UserManager {
  const settings: UserManagerSettings = {
    authority: config.authority,
    client_id: config.client_id,
    redirect_uri: `${window.location.origin}/auth/callback`,
    post_logout_redirect_uri: `${window.location.origin}/loggedout`,
    scope: config.scope,
    response_type: 'code',
  };
  return new UserManager(settings);
}
