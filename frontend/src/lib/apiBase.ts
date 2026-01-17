const fallback = import.meta.env.DEV ? "http://localhost:8000" : "https://hospital-stain-tracker-data-pipeline-production.up.railway.app";
export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? fallback).replace(/\/$/, "");
