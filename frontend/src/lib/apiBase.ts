const API_BASE =
  import.meta.env.PROD
    ? "https://hospital-stain-tracker-data-pipeline-production.up.railway.app"
    : "http://localhost:8080";

export default API_BASE;
