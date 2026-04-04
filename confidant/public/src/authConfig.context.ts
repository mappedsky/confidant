import { createContext } from 'react';
import type { UserManager } from 'oidc-client-ts';
import type { OidcConfig } from './types/api';

export interface AuthConfig {
  auth_required: boolean;
  oidc: OidcConfig | null;
  userManager: UserManager | null;
}

export const AuthConfigContext = createContext<AuthConfig>({
  auth_required: true,
  oidc: null,
  userManager: null,
});
