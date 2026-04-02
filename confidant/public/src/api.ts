import {
  ApiError,
  ApiErrorData,
  ClientConfigResponse,
  CredentialDetail,
  CredentialsListResponse,
  CredentialServicesResponse,
  GenerateValueResponse,
  GrantsResponse,
  ServicesListResponse,
  ServiceDetail,
  UserEmailResponse,
} from './types/api';

let xsrfCookieName: string | null = null;

export function setXsrfCookieName(name: string) {
  xsrfCookieName = name;
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
  if (xsrfCookieName) {
    const token = getCookie(xsrfCookieName);
    if (token) {
      headers.set('X-XSRF-TOKEN', token);
    }
  }
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    if (window.location.pathname !== '/v1/login') {
      window.location.href = '/v1/login';
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

export const api = {
  getClientConfig: () => request<ClientConfigResponse>('/v1/client_config'),
  getUserEmail: () => request<UserEmailResponse>('/v1/user/email'),

  getCredentials: () => request<CredentialsListResponse>('/v1/credentials'),
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
  getCredentialRevisions: (id: string) =>
    request<CredentialsListResponse>(`/v1/archive/credentials/${id}`),
  getCredentialDiff: (id: string, oldRev: number | string, newRev: number | string) =>
    request<CredentialDetail>(`/v1/credentials/${id}/${oldRev}/${newRev}`),
  revertCredential: (id: string, revision: number | string) =>
    request<CredentialDetail>(`/v1/credentials/${id}/${revision}`, {
      method: 'PUT',
    }),

  getServices: () => request<ServicesListResponse>('/v1/services'),
  getService: (id: string, metadataOnly = true) =>
    request<ServiceDetail>(`/v1/services/${id}?metadata_only=${metadataOnly}`),
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
  getServiceRevisions: (id: string) =>
    request<ServicesListResponse>(`/v1/archive/services/${id}`),
  getServiceDiff: (id: string, oldRev: number | string, newRev: number | string) =>
    request<ServiceDetail>(`/v1/services/${id}/${oldRev}/${newRev}`),
  revertService: (id: string, revision: number | string) =>
    request<ServiceDetail>(`/v1/services/${id}/${revision}`, {
      method: 'PUT',
    }),

  getRoles: () => request<{ roles: string[] }>('/v1/roles'),

  getGrants: (id: string) => request<GrantsResponse>(`/v1/grants/${id}`),
  updateGrants: (id: string) =>
    request<GrantsResponse>(`/v1/grants/${id}`, { method: 'PUT' }),

  generateValue: () => request<GenerateValueResponse>('/v1/value_generator'),
};
