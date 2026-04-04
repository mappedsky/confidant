import {
  UserManager,
  type OidcMetadata,
  type UserManagerSettings,
} from 'oidc-client-ts';
import type { OidcConfig } from './types/api';

function normalizeAuthority(authority: string): string {
  return authority.replace(/\/+$/, '');
}

function buildDevProxyMetadata(authority: string): Partial<OidcMetadata> | undefined {
  const normalizedAuthority = normalizeAuthority(authority);
  const authorityUrl = new URL(normalizedAuthority);
  const currentUrl = new URL(window.location.origin);

  const isFrontendDev =
    currentUrl.hostname === 'localhost' &&
    currentUrl.port === '3000';
  const isLocalOidc =
    authorityUrl.protocol === 'http:' &&
    authorityUrl.hostname === 'localhost' &&
    authorityUrl.port === '9000';

  if (!isFrontendDev || !isLocalOidc) {
    return undefined;
  }

  const providerOrigin = `${authorityUrl.protocol}//${authorityUrl.host}`;
  const oauthBasePath = '/application/o';
  const proxiedOauthBase = `${window.location.origin}${oauthBasePath}`;

  return {
    issuer: normalizedAuthority,
    authorization_endpoint: `${providerOrigin}${oauthBasePath}/authorize/`,
    token_endpoint: `${proxiedOauthBase}/token/`,
    userinfo_endpoint: `${proxiedOauthBase}/userinfo/`,
    jwks_uri: `${window.location.origin}${authorityUrl.pathname}/jwks/`,
    end_session_endpoint: `${normalizedAuthority}/end-session/`,
  };
}

export function createUserManager(config: OidcConfig): UserManager {
  const metadata = buildDevProxyMetadata(config.authority);
  const settings: UserManagerSettings = {
    authority: config.authority,
    ...(metadata ? { metadata } : {}),
    client_id: config.client_id,
    redirect_uri: `${window.location.origin}/auth/callback`,
    post_logout_redirect_uri: `${window.location.origin}/loggedout`,
    scope: config.scope,
    response_type: 'code',
  };
  return new UserManager(settings);
}
