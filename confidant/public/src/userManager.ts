import {
  UserManager,
  type OidcMetadata,
  type UserManagerSettings,
} from 'oidc-client-ts';
import type { OidcConfig } from './types/api';

function localizeDevOidcMetadata(metadata?: Partial<OidcMetadata>): Partial<OidcMetadata> | undefined {
  if (!metadata) {
    return undefined;
  }

  if (!import.meta.env.DEV) {
    return metadata;
  }

  const localized: Partial<OidcMetadata> = { ...metadata };
  type OidcEndpointKey = Exclude<
    keyof OidcMetadata,
    | 'issuer'
    | 'authorization_endpoint'
    | 'end_session_endpoint'
    | 'response_types_supported'
    | 'subject_types_supported'
    | 'id_token_signing_alg_values_supported'
  >;
  const endpointKeys: OidcEndpointKey[] = [
    'token_endpoint',
    'userinfo_endpoint',
    'jwks_uri',
    'revocation_endpoint',
    'introspection_endpoint',
    'registration_endpoint',
  ];

  for (const key of endpointKeys) {
    const value = localized[key];
    if (typeof value !== 'string') {
      continue;
    }

    const url = new URL(value, window.location.origin);
    if (url.origin !== window.location.origin) {
      localized[key] = `${window.location.origin}${url.pathname}${url.search}${url.hash}` as never;
    }
  }

  return localized;
}

export function createUserManager(config: OidcConfig): UserManager {
  const metadata = localizeDevOidcMetadata(config.metadata);
  const settings: UserManagerSettings = {
    authority: config.authority,
    ...(metadata ? { metadata: metadata as OidcMetadata } : {}),
    client_id: config.client_id,
    redirect_uri: `${window.location.origin}/auth/callback`,
    post_logout_redirect_uri: `${window.location.origin}/loggedout`,
    scope: config.scope,
    response_type: 'code',
  };
  return new UserManager(settings);
}
