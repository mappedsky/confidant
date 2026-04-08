import {
  ApiError,
  ApiErrorData,
  ClientConfigResponse,
  CreateSecretPayload,
  SecretDetail,
  SecretVersionsResponse,
  SecretsListResponse,
  SecretGroupsResponse,
  GenerateValueResponse,
  GenerateValueRequest,
  GroupWritePayload,
  GroupVersionsResponse,
  GroupsListResponse,
  GroupDetail,
  UserEmailResponse,
} from './types/api';
import { encodeSecretId } from './utils/resourceIds';

let xsrfCookieName: string | null = null;
let accessTokenGetter: (() => string | null) | null = null;
let unauthorizedHandler: (() => Promise<unknown> | unknown) | null = null;

interface CursorPageParams {
  limit?: number;
  page?: string | null;
  prefix?: string | null;
}

export function setXsrfCookieName(name: string) {
  xsrfCookieName = name;
}

export function setAccessTokenGetter(getter: (() => string | null) | null) {
  accessTokenGetter = getter;
}

export function setUnauthorizedHandler(handler: (() => Promise<unknown> | unknown) | null) {
  unauthorizedHandler = handler;
}

function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() ?? null;
  }
  return null;
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');
  const accessToken = accessTokenGetter?.();
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }
  if (xsrfCookieName) {
    const token = getCookie(xsrfCookieName);
    if (token) {
      headers.set('X-XSRF-TOKEN', token);
    }
  }
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    if (unauthorizedHandler) {
      await unauthorizedHandler();
    } else if (window.location.pathname !== '/') {
      window.location.href = '/';
    }
    return new Promise<T>(() => {});
  }
  if (!res.ok) {
    let errorData: ApiErrorData | undefined;
    try {
      errorData = (await res.json()) as ApiErrorData;
    } catch {
      errorData = undefined;
    }
    const err = new Error(errorData?.error ?? `HTTP ${res.status}`) as ApiError;
    err.status = res.status;
    err.data = errorData;
    throw err;
  }
  return res.json();
}

function withCursorParams(url: string, params?: CursorPageParams): string {
  if (!params) {
    return url;
  }

  const searchParams = new URLSearchParams();
  if (params.limit != null) {
    searchParams.set('limit', String(params.limit));
  }
  if (params.page) {
    searchParams.set('page', params.page);
  }
  if (params.prefix) {
    searchParams.set('prefix', params.prefix);
  }

  const query = searchParams.toString();
  return query ? `${url}?${query}` : url;
}

export const api = {
  getClientConfig: () => request<ClientConfigResponse>('/v1/client_config'),
  getUserEmail: () => request<UserEmailResponse>('/v1/user/email'),

  getSecrets: (params?: CursorPageParams) =>
    request<SecretsListResponse>(withCursorParams('/v1/secrets', params)),
  getSecret: (id: string, metadataOnly = true) =>
    request<SecretDetail>(
      `/v1/secrets/${encodeSecretId(id)}?metadata_only=${metadataOnly}`,
    ),
  decryptSecret: (id: string) =>
    request<SecretDetail>(`/v1/secrets/${encodeSecretId(id)}/decrypt`, {
      method: 'POST',
    }),
  createSecret: (data: CreateSecretPayload) =>
    request<SecretDetail>('/v1/secrets', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateSecret: (id: string, data: CreateSecretPayload | unknown) =>
    request<SecretDetail>(`/v1/secrets/${encodeSecretId(id)}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  deleteSecret: (id: string) =>
    request<SecretDetail>(`/v1/secrets/${encodeSecretId(id)}`, {
      method: 'DELETE',
    }),
  getSecretGroups: (id: string) =>
    request<SecretGroupsResponse>(`/v1/secrets/${encodeSecretId(id)}/groups`),
  getSecretVersions: (id: string) =>
    request<SecretVersionsResponse>(`/v1/secrets/${encodeSecretId(id)}/versions`),
  getSecretVersion: (id: string, version: number | string) =>
    request<SecretDetail>(
      `/v1/secrets/${encodeSecretId(id)}/versions/${version}`,
    ),
  decryptSecretVersion: (id: string, version: number | string) =>
    request<SecretDetail>(
      `/v1/secrets/${encodeSecretId(id)}/versions/${version}/decrypt`,
      {
        method: 'POST',
      },
    ),
  restoreSecretVersion: (id: string, version: number | string) =>
    request<SecretDetail>(
      `/v1/secrets/${encodeSecretId(id)}/versions/${version}/restore`,
      {
        method: 'POST',
      },
    ),

  getGroups: (params?: CursorPageParams) =>
    request<GroupsListResponse>(withCursorParams('/v1/groups', params)),
  getGroup: (id: string) =>
    request<GroupDetail>(`/v1/groups/${id}`),
  createGroup: (id: string, data: GroupWritePayload) =>
    request<GroupDetail>(`/v1/groups/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  updateGroup: (id: string, data: GroupWritePayload) =>
    request<GroupDetail>(`/v1/groups/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  deleteGroup: (id: string) =>
    request<GroupDetail>(`/v1/groups/${id}`, {
      method: 'DELETE',
    }),
  getGroupVersions: (id: string) =>
    request<GroupVersionsResponse>(`/v1/groups/${id}/versions`),
  getGroupVersion: (id: string, version: number | string) =>
    request<GroupDetail>(`/v1/groups/${id}/versions/${version}`),
  restoreGroupVersion: (id: string, version: number | string) =>
    request<GroupDetail>(`/v1/groups/${id}/versions/${version}/restore`, {
      method: 'POST',
    }),
  generateValue: (params?: GenerateValueRequest) => {
    const searchParams = new URLSearchParams();
    if (params?.length != null) {
      searchParams.set('length', String(params.length));
    }
    if (params?.complexity?.length) {
      for (const value of params.complexity) {
        searchParams.append('complexity', value);
      }
    }
    const query = searchParams.toString();
    return request<GenerateValueResponse>(
      query ? `/v1/value_generator?${query}` : '/v1/value_generator',
    );
  },
};
