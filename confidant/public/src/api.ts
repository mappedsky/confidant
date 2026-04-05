import {
  ApiError,
  ApiErrorData,
  ClientConfigResponse,
  SecretDetail,
  SecretVersionsResponse,
  SecretsListResponse,
  SecretGroupsResponse,
  GenerateValueResponse,
  GroupVersionsResponse,
  GroupsListResponse,
  GroupDetail,
  UserEmailResponse,
} from './types/api';

let xsrfCookieName: string | null = null;
let accessTokenGetter: (() => string | null) | null = null;
let unauthorizedHandler: (() => Promise<unknown> | unknown) | null = null;

interface CursorPageParams {
  limit?: number;
  page?: string | null;
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

  const query = searchParams.toString();
  return query ? `${url}?${query}` : url;
}

export const api = {
  getClientConfig: () => request<ClientConfigResponse>('/v1/client_config'),
  getUserEmail: () => request<UserEmailResponse>('/v1/user/email'),

  getSecrets: (params?: CursorPageParams) =>
    request<SecretsListResponse>(withCursorParams('/v1/secrets', params)),
  getSecret: (id: string, metadataOnly = true) =>
    request<SecretDetail>(`/v1/secrets/${id}?metadata_only=${metadataOnly}`),
  createSecret: (data: unknown) =>
    request<SecretDetail>('/v1/secrets', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateSecret: (id: string, data: unknown) =>
    request<SecretDetail>(`/v1/secrets/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  getSecretGroups: (id: string) =>
    request<SecretGroupsResponse>(`/v1/secrets/${id}/groups`),
  getSecretVersions: (id: string) =>
    request<SecretVersionsResponse>(`/v1/secrets/${id}/versions`),
  getSecretVersion: (id: string, version: number | string) =>
    request<SecretDetail>(`/v1/secrets/${id}/versions/${version}`),
  restoreSecretVersion: (id: string, version: number | string) =>
    request<SecretDetail>(`/v1/secrets/${id}/versions/${version}/restore`, {
      method: 'POST',
    }),

  getGroups: (params?: CursorPageParams) =>
    request<GroupsListResponse>(withCursorParams('/v1/groups', params)),
  getGroup: (id: string) =>
    request<GroupDetail>(`/v1/groups/${id}`),
  createGroup: (id: string, data: unknown) =>
    request<GroupDetail>(`/v1/groups/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  updateGroup: (id: string, data: unknown) =>
    request<GroupDetail>(`/v1/groups/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  getGroupVersions: (id: string) =>
    request<GroupVersionsResponse>(`/v1/groups/${id}/versions`),
  getGroupVersion: (id: string, version: number | string) =>
    request<GroupDetail>(`/v1/groups/${id}/versions/${version}`),
  restoreGroupVersion: (id: string, version: number | string) =>
    request<GroupDetail>(`/v1/groups/${id}/versions/${version}/restore`, {
      method: 'POST',
    }),
  generateValue: () => request<GenerateValueResponse>('/v1/value_generator'),
};
