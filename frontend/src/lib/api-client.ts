import { PrismResponse, type ApiErrorShape } from "./types";

const DEFAULT_BASE_URL = "http://localhost:8000";

export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? DEFAULT_BASE_URL;

export class PrismApiError extends Error {
  public status: number;
  public payload: ApiErrorShape | null;

  constructor(status: number, message: string, payload: ApiErrorShape | null = null) {
    super(message);
    this.name = "PrismApiError";
    this.status = status;
    this.payload = payload;
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
  headers?: Record<string, string>;
  authorization?: string | null;
  mode?: "demo" | "learn";
  expectEnvelope?: boolean;
};

const buildHeaders = (options: RequestOptions): HeadersInit => {
  const headers = new Headers(options.headers ?? {});
  if (options.authorization) {
    headers.set("Authorization", options.authorization);
  }
  if (options.mode === "learn") {
    headers.set("X-Prism-Mode", "learn");
  }
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return headers;
};

const parseError = async (response: Response): Promise<ApiErrorShape | null> => {
  try {
    const text = await response.text();
    if (!text) {
      return null;
    }
    return JSON.parse(text) as ApiErrorShape;
  } catch {
    return null;
  }
};

export async function prismFetch<T>(path: string, options: RequestOptions = {}): Promise<PrismResponse<T>> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: options.method ?? (options.body ? "POST" : "GET"),
    body: options.body ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
    headers: buildHeaders(options),
  });

  if (!response.ok) {
    const payload = await parseError(response);
    const detail = payload?.detail ?? payload?.message ?? response.statusText;
    throw new PrismApiError(response.status, detail, payload);
  }

  if (response.status === 204) {
    return { data: null as T, meta: {} };
  }

  const json = (await response.json()) as PrismResponse<T>;
  return json;
}

export async function rawFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: options.method ?? (options.body ? "POST" : "GET"),
    body: options.body ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
    headers: buildHeaders(options),
  });

  if (!response.ok) {
    const payload = await parseError(response);
    const detail = payload?.detail ?? payload?.message ?? response.statusText;
    throw new PrismApiError(response.status, detail, payload);
  }

  if (response.status === 204) {
    return null as T;
  }

  return (await response.json()) as T;
}
