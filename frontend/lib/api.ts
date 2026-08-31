// Centralized API client for the PromptDNA frontend.
//
// Everything that talks to FastAPI goes through `request()`: it resolves the
// base URL from NEXT_PUBLIC_API_BASE_URL, attaches the bearer token, parses
// JSON, and turns failures into a typed `ApiError` with a human-readable
// message. UI components import the named functions below — they never call
// `fetch` directly.
//
// Token storage: localStorage (Phase 3 decision). Trade-off: readable by any
// script on the origin, so an XSS would leak the token. Not production-secure;
// a production build should use an HttpOnly cookie. See docs/decisions.md.

import type {
  Experiment,
  ExperimentListResponse,
  ExperimentRunPayload,
  ListPromptsParams,
  Model,
  Prompt,
  PromptCreatePayload,
  PromptListResponse,
  PromptMetadataPayload,
  User,
  Version,
  VersionCreatePayload,
  VersionListResponse,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const TOKEN_KEY = "promptdna.access_token";

// --- token helpers ----------------------------------------------------------

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* storage unavailable — token simply won't persist */
  }
}

export function clearToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

// --- errors ---------------------------------------------------------------

export class ApiError extends Error {
  /** HTTP status, or 0 for a network / CORS failure. */
  status: number;
  /** Raw `detail` string from the backend, when present. */
  detail?: string;

  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** A friendly, user-facing sentence for an ApiError (never raw JSON). */
export function friendlyMessage(err: unknown): string {
  if (!(err instanceof ApiError)) {
    return "Something went wrong. Please try again.";
  }
  switch (err.status) {
    case 0:
      return "Unable to connect to the server. Check that the API is running.";
    case 401:
      return "Your session has expired. Please log in again.";
    case 403:
      return "You don't have permission to do that.";
    case 404:
      return err.detail ?? "Not found.";
    case 409:
      return err.detail ?? "That action conflicts with the current state. Please try again.";
    case 422:
      return err.detail ?? "Some of the information provided is invalid.";
    case 500:
      return "The server ran into a problem. Please try again later.";
    case 503:
      return "The service is temporarily unavailable. Please try again shortly.";
    default:
      return err.detail ?? err.message ?? "Request failed.";
  }
}

// --- core request ------------------------------------------------------

interface RequestOptions {
  method?: string;
  body?: unknown;
  /** form-encoded body (used only by login's OAuth2 password flow) */
  form?: Record<string, string>;
  auth?: boolean; // attach the bearer token (default true)
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, form, auth = true } = opts;
  const headers: Record<string, string> = {};

  let payload: BodyInit | undefined;
  if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = new URLSearchParams(form).toString();
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { method, headers, body: payload });
  } catch {
    throw new ApiError(0, "Unable to connect to the server.");
  }

  if (res.status === 204) return undefined as T;

  let data: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, `Request failed (${res.status})`, extractDetail(data));
  }
  return data as T;
}

function extractDetail(data: unknown): string | undefined {
  if (data && typeof data === "object" && "detail" in data) {
    const d = (data as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    // FastAPI 422: detail is an array of {loc, msg, ...}
    if (Array.isArray(d) && d.length > 0) {
      const first = d[0] as { msg?: string; loc?: unknown[] };
      if (first?.msg) {
        const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : undefined;
        return field ? `${field}: ${first.msg}` : first.msg;
      }
    }
  }
  return undefined;
}

// --- auth (Phase 3) --------------------------------------------------

export async function register(
  name: string,
  email: string,
  password: string,
): Promise<User> {
  return request<User>("/api/v1/auth/register", {
    method: "POST",
    body: { name, email, password },
    auth: false,
  });
}

export async function login(email: string, password: string): Promise<string> {
  const data = await request<{ access_token: string }>("/api/v1/auth/login", {
    method: "POST",
    form: { username: email, password },
    auth: false,
  });
  return data.access_token;
}

/** Resolve the current user from the stored bearer token. */
export async function getCurrentUser(): Promise<User> {
  return request<User>("/api/v1/auth/me");
}

// --- prompts (Phase 2 / 4A) ---------------------------------------

export async function listPrompts(
  params: ListPromptsParams = {},
): Promise<PromptListResponse> {
  const qs = new URLSearchParams();
  qs.set("limit", String(params.limit ?? 20));
  qs.set("offset", String(params.offset ?? 0));
  if (params.search) qs.set("search", params.search);
  if (params.isPublic !== undefined) qs.set("is_public", String(params.isPublic));
  return request<PromptListResponse>(`/api/v1/prompts?${qs.toString()}`);
}

export async function getPrompt(promptId: string): Promise<Prompt> {
  return request<Prompt>(`/api/v1/prompts/${promptId}`);
}

export async function createPrompt(payload: PromptCreatePayload): Promise<Prompt> {
  return request<Prompt>("/api/v1/prompts", { method: "POST", body: payload });
}

export async function updatePromptMetadata(
  promptId: string,
  payload: PromptMetadataPayload,
): Promise<Prompt> {
  return request<Prompt>(`/api/v1/prompts/${promptId}`, {
    method: "PATCH",
    body: payload,
  });
}

// --- versions (Phase 4A) ---------------------------------------

export async function getVersions(promptId: string): Promise<VersionListResponse> {
  return request<VersionListResponse>(`/api/v1/prompts/${promptId}/versions`);
}

export async function getVersion(
  promptId: string,
  versionId: string,
): Promise<Version> {
  return request<Version>(`/api/v1/prompts/${promptId}/versions/${versionId}`);
}

export async function createVersion(
  promptId: string,
  payload: VersionCreatePayload,
): Promise<Version> {
  return request<Version>(`/api/v1/prompts/${promptId}/versions`, {
    method: "POST",
    body: payload,
  });
}

// --- experiments / models (Phase 5) -----------------------------

export async function listModels(): Promise<Model[]> {
  return request<Model[]>("/api/v1/models");
}

export async function listPromptExperiments(
  promptId: string,
): Promise<ExperimentListResponse> {
  return request<ExperimentListResponse>(
    `/api/v1/prompts/${promptId}/experiments`,
  );
}

export async function runExperiment(
  promptId: string,
  versionId: string,
  payload: ExperimentRunPayload,
): Promise<Experiment> {
  return request<Experiment>(
    `/api/v1/prompts/${promptId}/versions/${versionId}/experiments`,
    { method: "POST", body: payload },
  );
}

export async function getExperiment(experimentId: string): Promise<Experiment> {
  return request<Experiment>(`/api/v1/experiments/${experimentId}`);
}

export async function updateExperimentScore(
  experimentId: string,
  payload: { score?: number | null; notes?: string | null },
): Promise<Experiment> {
  return request<Experiment>(`/api/v1/experiments/${experimentId}`, {
    method: "PATCH",
    body: payload,
  });
}
