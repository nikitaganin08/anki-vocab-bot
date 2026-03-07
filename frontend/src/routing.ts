const WEBAPP_PATH_SEGMENT = "/telegram/webapp";
const WEBAPP_BASENAME_PATTERN = /^(.*\/telegram\/webapp)(?:\/.*)?$/;

export function resolveWebAppBasename(pathname = window.location.pathname): string | undefined {
  const match = pathname.match(WEBAPP_BASENAME_PATTERN);
  return match?.[1];
}

export function resolveApiPath(path: string, pathname = window.location.pathname): string {
  const basename = resolveWebAppBasename(pathname);
  if (!basename) {
    return path;
  }

  const prefix = basename.slice(0, -WEBAPP_PATH_SEGMENT.length);
  return `${prefix}${path}`;
}
