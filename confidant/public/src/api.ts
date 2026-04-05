import {
  ApiError,
  ApiErrorData,
  ClientConfigResponse,
  CredentialDetail,
  CredentialVersionsResponse,
  CredentialsListResponse,
  CredentialServicesResponse,
  GenerateValueResponse,
  ServiceVersionsResponse,
  ServicesListResponse,
  ServiceDetail,
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

  getCredentials: (params?: CursorPageParams) =>
    request<CredentialsListResponse>(withCursorParams('/v1/credentials', params)),
  getCredential: (id: string, metadataOnly = true) =>
    request<CredentialDetail>(`/v1/credentials/${id}?metadata_only=${metadataOnly}`),
  createCredential: (data: unknown) =>
    request<CredentialDetail>('/v1/credentials', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateCredential: (id: string, data: unknown) =>
    request<CredentialDetail>(`/v1/credentials/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  getCredentialServices: (id: string) =>
    request<CredentialServicesResponse>(`/v1/credentials/${id}/services`),
  getCredentialVersions: (id: string) =>
    request<CredentialVersionsResponse>(`/v1/credentials/${id}/versions`),
  getCredentialVersion: (id: string, version: number | string) =>
    request<CredentialDetail>(`/v1/credentials/${id}/versions/${version}`),
  restoreCredentialVersion: (id: string, version: number | string) =>
    request<CredentialDetail>(`/v1/credentials/${id}/versions/${version}/restore`, {
      method: 'POST',
    }),

  getServices: (params?: CursorPageParams) =>
    request<ServicesListResponse>(withCursorParams('/v1/services', params)),
  getService: (id: string) =>
    request<ServiceDetail>(`/v1/services/${id}`),
  createService: (id: string, data: unknown) =>
    request<ServiceDetail>(`/v1/services/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  updateService: (id: string, data: unknown) =>
    request<ServiceDetail>(`/v1/services/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  getServiceVersions: (id: string) =>
    request<ServiceVersionsResponse>(`/v1/services/${id}/versions`),
  getServiceVersion: (id: string, version: number | string) =>
    request<ServiceDetail>(`/v1/services/${id}/versions/${version}`),
  restoreServiceVersion: (id: string, version: number | string) =>
    request<ServiceDetail>(`/v1/services/${id}/versions/${version}/restore`, {
      method: 'POST',
    }),
  generateValue: () => request<GenerateValueResponse>('/v1/value_generator'),
};
