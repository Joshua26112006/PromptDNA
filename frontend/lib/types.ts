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
