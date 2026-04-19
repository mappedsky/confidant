import type { OidcMetadata } from 'oidc-client-ts';

export interface EntityPermissions {
  metadata?: boolean;
  decrypt?: boolean;
  get?: boolean;
  revert?: boolean;
  update?: boolean;
  delete?: boolean;
  create?: boolean;
  list?: boolean;
}

export interface ClientConfigPermissions {
  secrets: {
    list: boolean;
    create: boolean;
  };
  groups: {
    list: boolean;
    create: boolean;
  };
}

export interface OidcConfig {
  authority: string;
  client_id: string;
  redirect_uri: string;
  scope: string;
  metadata?: Partial<OidcMetadata>;
}

export interface AuthConfigResponse {
  auth_required: boolean;
  oidc: OidcConfig | null;
}

export interface ClientConfigGenerated {
  defined_tags: string[];
  permissions: ClientConfigPermissions;
}

export interface ClientConfigResponse {
  generated: ClientConfigGenerated;
}

export interface UserEmailResponse {
  email: string | null;
}

export interface SecretIdentifier {
  id: string;
}

export interface CreateSecretPayload {
  id: string;
  name: string;
  secret_pairs: Record<string, string>;
  metadata: Record<string, string>;
  documentation: string;
  tags: string[];
}

export interface SecretBase {
  id: string;
  name: string;
  revision: number;
  modified_date?: string;
  modified_by?: string;
  documentation?: string | null;
  tags?: string[];
  permissions?: EntityPermissions;
}

export interface SecretSummary extends SecretBase {
  metadata?: Record<string, string>;
}

export interface SecretDetail extends SecretBase {
  secret_keys: string[];
  secret_pairs: Record<string, string>;
  metadata: Record<string, string>;
  last_rotation_date?: string | null;
  next_rotation_date?: string | null;
}

export interface SecretsListResponse {
  secrets: SecretSummary[];
  next_page?: string | null;
}

export interface SecretVersionsResponse {
  versions: SecretSummary[];
  next_page?: string | null;
}

export interface SecretGroupsResponse {
  groups: SecretIdentifier[];
}

export type GroupPolicies = Record<string, string[]>;

export interface GroupWritePayload {
  id?: string;
  policies: GroupPolicies;
}

export interface GroupBase {
  id: string;
  revision: number;
  modified_date?: string;
  modified_by?: string;
  permissions?: EntityPermissions;
}

export interface GroupSummary extends GroupBase {
  policies: GroupPolicies;
}

export interface GroupDetail extends GroupBase {
  policies: GroupPolicies;
}

export interface GroupsListResponse {
  groups: GroupSummary[];
  next_page?: string | null;
}

export interface GroupVersionsResponse {
  versions: GroupSummary[];
  next_page?: string | null;
}

export interface GenerateValueResponse {
  value: string;
}

export interface GenerateValueRequest {
  length?: number;
  complexity?: string[];
}

export type ConflictInfo = {
  secrets?: string[];
  groups?: string[];
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
