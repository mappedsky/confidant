let xsrfCookieName = null;

export function setXsrfCookieName(name) {
  xsrfCookieName = name;
}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

async function request(url, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (xsrfCookieName) {
    const token = getCookie(xsrfCookieName);
    if (token) {
      headers['X-XSRF-TOKEN'] = token;
    }
  }
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    // Not authenticated — redirect to the login endpoint which initiates the
    // configured auth flow (SAML etc.).  After authentication the backend
    // redirects back to / where the app re-loads with a valid session.
    window.location.href = '/v1/login';
    // Return a promise that never resolves so callers don't continue.
    return new Promise(() => {});
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const err = new Error(data.error || `HTTP ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return res.json();
}

export const api = {
  getClientConfig: () => request('/v1/client_config'),
  getUserEmail: () => request('/v1/user/email'),

  // Credentials
  getCredentials: () => request('/v1/credentials'),
  getCredential: (id, metadataOnly = true) =>
    request(`/v1/credentials/${id}?metadata_only=${metadataOnly}`),
  createCredential: (data) =>
    request('/v1/credentials', { method: 'POST', body: JSON.stringify(data) }),
  updateCredential: (id, data) =>
    request(`/v1/credentials/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  getCredentialServices: (id) => request(`/v1/credentials/${id}/services`),
  getCredentialRevisions: (id) => request(`/v1/archive/credentials/${id}`),
  getCredentialDiff: (id, oldRev, newRev) =>
    request(`/v1/credentials/${id}/${oldRev}/${newRev}`),
  revertCredential: (id, revision) =>
    request(`/v1/credentials/${id}/${revision}`, { method: 'PUT' }),

  // Services
  getServices: () => request('/v1/services'),
  getService: (id) => request(`/v1/services/${id}`),
  createService: (data) =>
    request('/v1/services', { method: 'POST', body: JSON.stringify(data) }),
  updateService: (id, data) =>
    request(`/v1/services/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  getServiceRevisions: (id) => request(`/v1/archive/services/${id}`),
  getServiceDiff: (id, oldRev, newRev) =>
    request(`/v1/services/${id}/${oldRev}/${newRev}`),
  revertService: (id, revision) =>
    request(`/v1/services/${id}/${revision}`, { method: 'PUT' }),

  // Roles
  getRoles: () => request('/v1/roles'),

  // Grants
  getGrants: (id) => request(`/v1/grants/${id}`),
  updateGrants: (id) => request(`/v1/grants/${id}`, { method: 'PUT' }),

  // Value generator
  generateValue: () => request('/v1/value_generator'),
};
