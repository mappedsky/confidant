export interface EntityPermissions {
  metadata?: boolean;
  read?: boolean;
  read_with_alert?: boolean;
  get?: boolean;
  update?: boolean;
  create?: boolean;
  list?: boolean;
}

export interface ClientConfigPermissions {
  credentials: {
    list: boolean;
    create: boolean;
  };
  services: {
    list: boolean;
    create: boolean;
  };
}

export interface OidcConfig {
  authority: string;
  client_id: string;
  redirect_uri: string;
  scope: string;
}

export interface ClientConfigGenerated {
  auth_required: boolean;
  oidc: OidcConfig | null;
  xsrf_cookie_name: string;
  maintenance_mode: boolean;
  history_page_limit: number;
  defined_tags: string[];
  permissions: ClientConfigPermissions;
}

export interface ClientConfigResponse {
  defined: Record<string, unknown>;
  generated: ClientConfigGenerated;
}

export interface AuthConfigResponse {
  auth_required: boolean;
  oidc: OidcConfig | null;
}

export interface UserEmailResponse {
  email: string | null;
}

export interface CredentialIdentifier {
  id: string;
  enabled?: boolean;
}

export interface CredentialBase {
  id: string;
  name: string;
  revision: number;
  enabled: boolean;
  modified_date?: string;
  modified_by?: string;
  documentation?: string | null;
  tags?: string[];
  permissions?: EntityPermissions;
}

export interface CredentialSummary extends CredentialBase {
  metadata?: Record<string, string>;
}

export interface CredentialDetail extends CredentialBase {
  credential_keys: string[];
  credential_pairs: Record<string, string>;
  metadata: Record<string, string>;
  last_rotation_date?: string | null;
  next_rotation_date?: string | null;
}

export interface CredentialsListResponse {
  credentials: CredentialSummary[];
}

export interface CredentialServicesResponse {
  services: CredentialIdentifier[];
}

export interface ServiceBase {
  id: string;
  revision: number;
  enabled: boolean;
  modified_date?: string;
  modified_by?: string;
  permissions?: EntityPermissions;
}

export interface ServiceSummary extends ServiceBase {
  credentials: string[];
}

export interface ServiceDetail extends ServiceBase {
  credentials: string[];
}

export interface ServicesListResponse {
  services: ServiceSummary[];
}

export interface GenerateValueResponse {
  value: string;
}

export type ConflictInfo = {
  credentials?: string[];
  services?: string[];
};

export type ConflictMap = Record<string, ConflictInfo>;

export interface ApiErrorData {
  error?: string;
  reference?: string;
  conflicts?: ConflictMap;
}

export interface ApiError extends Error {
  status?: number;
  data?: ApiErrorData;
}
