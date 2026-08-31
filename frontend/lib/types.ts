// TypeScript shapes mirroring the FastAPI response schemas. Kept in sync with
// backend/app/schemas/{auth,prompt}.py.

export interface User {
  user_id: string;
  name: string;
  email: string;
  created_at: string;
}

export interface Owner {
  user_id: string;
  name: string;
}

export interface Version {
  version_id: string;
  prompt_id: string;
  version_number: number;
  content: string;
  change_summary: string | null;
  created_by: string;
  created_at: string;
}

/** Full detail — `GET /api/v1/prompts/{id}` and create/update responses. */
export interface Prompt {
  prompt_id: string;
  user_id: string;
  title: string;
  description: string | null;
  purpose: string | null;
  is_public: boolean;
  parent_prompt_id: string | null;
  created_at: string;
  updated_at: string;
  owner: Owner;
  versions: Version[];
  latest_version: Version | null;
  tags: string[];
}

/** One row of the paginated list — `GET /api/v1/prompts`. */
export interface PromptListItem {
  prompt_id: string;
  user_id: string;
  title: string;
  description: string | null;
  purpose: string | null;
  is_public: boolean;
  created_at: string;
  updated_at: string;
  latest_version_number: number | null;
}

export interface PromptListResponse {
  items: PromptListItem[];
  limit: number;
  offset: number;
  total: number;
}

export interface VersionListResponse {
  items: Version[];
  total: number;
}

// --- experiments / models (Phase 5) ----------------------------------------

export interface Model {
  model_id: string;
  name: string;
  provider: string;
  created_at: string;
  /** a registered provider for `provider` has credentials on this server */
  execution_configured: boolean;
}

export type ExperimentStatus = "PENDING" | "SUCCESS" | "FAILED";

export interface Experiment {
  experiment_id: string;
  version_id: string;
  prompt_id: string;
  model_id: string;
  model_name: string;
  provider: string;
  version_number: number;
  executed_at: string;
  response_time_ms: number | null;
  score: number | string | null;
  output: string | null;
  notes: string | null;
  status: ExperimentStatus;
  error_message: string | null;
}

export interface ExperimentListResponse {
  items: Experiment[];
  total: number;
}

export interface ExperimentRunPayload {
  model_id: string;
  notes?: string | null;
}

// --- semantic search (Phase 6) ------------------------------------------------

export interface SemanticSearchResult {
  prompt_id: string;
  version_id: string;
  prompt_title: string;
  version_number: number;
  content_preview: string;
  /** 1 - cosine_distance; higher = more semantically similar */
  similarity: number;
  is_public: boolean;
  created_at: string;
}

export interface SemanticSearchResponse {
  query: string;
  count: number;
  results: SemanticSearchResult[];
}

// --- request payloads ---------------------------------------------------------

export interface PromptCreatePayload {
  title: string;
  content: string;
  description?: string | null;
  purpose?: string | null;
  is_public: boolean;
  parent_prompt_id?: string | null;
}

export interface PromptMetadataPayload {
  title?: string;
  description?: string | null;
  purpose?: string | null;
  is_public?: boolean;
}

export interface VersionCreatePayload {
  content: string;
  change_summary?: string | null;
}

export interface ListPromptsParams {
  limit?: number;
  offset?: number;
  search?: string;
  isPublic?: boolean;
}
