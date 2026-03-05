const ADMIN_PATH_SEGMENT = "/admin";
const ADMIN_BASENAME_PATTERN = /^(.*\/admin)(?:\/.*)?$/;

export function resolveAdminBasename(pathname = window.location.pathname): string | undefined {
  const match = pathname.match(ADMIN_BASENAME_PATTERN);
  return match?.[1];
}

export function resolveApiPath(path: string, pathname = window.location.pathname): string {
  const basename = resolveAdminBasename(pathname);
  if (!basename) {
    return path;
  }

  const prefix = basename.slice(0, -ADMIN_PATH_SEGMENT.length);
  return `${prefix}${path}`;
}
