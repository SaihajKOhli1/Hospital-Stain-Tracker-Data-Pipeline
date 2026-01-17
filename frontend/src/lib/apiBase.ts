const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://hospital-stain-tracker-data-pipeline-production.up.railway.app";

export function apiUrl(path: string) {
  if (!path.startsWith("/")) path = "/" + path;
  return `${API_BASE}${path}`;
}
