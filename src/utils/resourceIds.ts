const secretIdPattern = /^[A-Za-z0-9/_+=.@-]{1,512}$/;
const groupIdPattern = /^[A-Za-z0-9_+=.@-]{1,512}$/;
const secretPolicyPattern = /^(?:[A-Za-z0-9/_+=.@\-*?\[\]]){1,512}$/;

export function validateSecretId(id: string): string | null {
  if (!id) {
    return 'ID is required.';
  }
  if (id.length > 512) {
    return 'ID must be 512 characters or fewer.';
  }
  if (id.endsWith('/')) {
    return 'Secret ID cannot end with /.';
  }
  if (!secretIdPattern.test(id)) {
    return 'Secret ID may only contain letters, numbers, and /_+=.@-.';
  }
  return null;
}

export function validateGroupId(id: string): string | null {
  if (!id) {
    return 'ID is required.';
  }
  if (id.length > 512) {
    return 'ID must be 512 characters or fewer.';
  }
  if (!groupIdPattern.test(id)) {
    return 'Group ID may only contain letters, numbers, and _+=.@-.';
  }
  return null;
}

export function secretPolicyHasGlob(value: string): boolean {
  return /[*?\[]/.test(value);
}

export function validateSecretPolicyPath(value: string): string | null {
  if (!value) {
    return 'Secret path or glob is required.';
  }
  if (!secretPolicyHasGlob(value)) {
    return validateSecretId(value);
  }
  if (value.length > 512) {
    return 'Secret path or glob must be 512 characters or fewer.';
  }
  if (value.endsWith('/')) {
    return 'Secret path or glob cannot end with /.';
  }
  if (!secretPolicyPattern.test(value)) {
    return 'Secret path or glob may only contain letters, numbers, and /_+=.@-*?[].';
  }
  return null;
}

export function encodeSecretId(id: string): string {
  return encodeURIComponent(id);
}

export function secretDetailPath(id: string): string {
  return `/secrets/${encodeSecretId(id)}`;
}

export function secretHistoryPath(id: string): string {
  return `${secretDetailPath(id)}/history`;
}

export function secretVersionPath(id: string, version: number | string): string {
  return `${secretDetailPath(id)}/versions/${version}`;
}
