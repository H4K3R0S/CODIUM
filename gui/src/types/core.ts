// ==========          CORE STATUS MODELI          ==========

export interface HealthResponse {
  status: string;
  version: string;
  active_domain: string;
}

// ==========          DOMAIN MODELI          ==========

export interface DomainView {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  active: boolean;
}

// ==========          CONTEXT MODELI          ==========

export interface CoreContext {
  session_id: string;
  active_domain_id: string;
  workspace_id: string | null;
  locale: string;
  timezone: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, string>;
}

export interface ContextUpdateRequest {
  active_domain_id?: string;
  workspace_id?: string | null;
  locale?: string;
  timezone?: string;
  metadata?: Record<string, string>;
}