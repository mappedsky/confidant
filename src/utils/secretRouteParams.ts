export interface ParsedSecretRoute {
  id: string | null;
  version: number | null;
  isHistory: boolean;
}

export function parseSecretRouteRemainder(
  remainder?: string,
): ParsedSecretRoute {
  if (!remainder) {
    return {
      id: null,
      version: null,
      isHistory: false,
    };
  }

  const segments = remainder.split('/');
  if (segments.length >= 3 && segments.at(-2) === 'versions') {
    const version = Number(segments.at(-1));
    if (!Number.isNaN(version)) {
      return {
        id: segments.slice(0, -2).join('/'),
        version,
        isHistory: false,
      };
    }
  }

  if (segments.at(-1) === 'history') {
    return {
      id: segments.slice(0, -1).join('/'),
      version: null,
      isHistory: true,
    };
  }

  return {
    id: remainder,
    version: null,
    isHistory: false,
  };
}
