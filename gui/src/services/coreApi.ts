import type { DomainView, HealthResponse } from "../types/core";
import type { CatalogModel } from "../features/settings/modelPicker";
import { deleteRequest, getJson, postJson, putJson } from "./httpClient";


// ==========          CORE FOUNDATION API          ==========

/**
 * Učitava osnovno stanje CORE runtime-a.
 */
export function getCoreHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/api/v1/health");
}

/**
 * Učitava sve domene registrovane unutar CORE sistema.
 */
export function getDomains(): Promise<DomainView[]> {
  return getJson<DomainView[]>("/api/v1/domains");
}

// ==========          KONEKTORI (API ključevi)          ==========
// Vrednost ključa ide SAMO u jednom smeru — u telu zahteva ka backend-u.
// Nijedan odgovor je ne vraća; `has_secret` je sve što GUI sme da zna.

export type ConnectorDto = {
  id: number;
  name: string;
  kind: string;
  config: Record<string, unknown>;
  has_secret: boolean;
  status: string;
  last_tested_at: string;
  last_error: string;
  created_at: string;
  updated_at: string;
};

export type ConnectorProbe = {
  ok: boolean;
  message: string;
  latency_ms: number | null;
};

export type ConnectorKindDto = {
  id: string;
  label: string;
  /** Vrsta bez provajdera je najava, ne ponuda — GUI je ne nudi. */
  supported: boolean;
  /** Polja koja forma traži; ekran ih ne nosi po vrsti nego čita odavde. */
  required_fields: string[];
  secret_fields: string[];
  /** Tajne bez kojih konektor radi (SSH ključ bez lozinke). */
  optional_secret_fields: string[];
};

// ----------          UPOTREBA KONEKTORA (CODIUM)          ----------
// Konektori su CORE, ali ko ih koristi zna samo domen — zato druga ruta.

export type ConnectorUsageItem = {
  area: string;
  id: number;
  name: string;
  label: string;
};

export type ConnectorUsage = {
  connector_id: number;
  items: ConnectorUsageItem[];
};

/** Šta u CODIUM-u koristi koji konektor. Potrebno pre brisanja. */
export function fetchConnectorUsage(): Promise<{ usage: ConnectorUsage[] }> {
  return getJson<{ usage: ConnectorUsage[] }>(
    "/api/v1/codium/integrations/usage",
  );
}

/** Vrste konektora koje sistem poznaje. */
export function listConnectorKinds(): Promise<{ kinds: ConnectorKindDto[] }> {
  return getJson<{ kinds: ConnectorKindDto[] }>(
    "/api/v1/core/ai/connectors/kinds",
  );
}

/** Postojeći konektori (bez tajni). */
export function listConnectors(): Promise<{ connectors: ConnectorDto[] }> {
  return getJson<{ connectors: ConnectorDto[] }>(
    "/api/v1/core/ai/connectors/",
  );
}

/** Pravi konektor; vrednost ključa odlazi u keychain i ne vraća se. */
export function createConnector(payload: {
  name: string;
  kind: string;
  secret: string;
}): Promise<ConnectorDto> {
  return postJson<ConnectorDto, typeof payload>(
    "/api/v1/core/ai/connectors/",
    payload,
  );
}

/** Menja vrednost ključa postojećeg konektora. */
export function updateConnectorSecret(
  connectorId: number,
  secret: string,
): Promise<ConnectorDto> {
  return putJson<ConnectorDto, { secret: string }>(
    `/api/v1/core/ai/connectors/${connectorId}/secret`,
    { secret },
  );
}

/** Briše konektor i njegovu tajnu iz keychain-a. */
export function deleteConnector(connectorId: number): Promise<void> {
  return deleteRequest<void>(`/api/v1/core/ai/connectors/${connectorId}`);
}

/** Proba konekcije; ishod se pamti uz konektor. */
export function testConnector(connectorId: number): Promise<ConnectorProbe> {
  return postJson<ConnectorProbe, Record<string, never>>(
    `/api/v1/core/ai/connectors/${connectorId}/test`,
    {},
  );
}


// ==========          GLOBALNI KATALOG MODELA          ==========
// CORE odlučuje koje modele uopšte nudi domenima. Domen sme da suzi taj izbor
// za sebe, ali ne i da vrati model koji je CORE isključio.

export type ModelScopeDto = { id: string; label: string };

/**
 * Opsezi u kojima se odlučuje o modelima.
 *
 * „global" važi svuda; ostalo su CORE i domeni. Spisak dolazi sa backend-a da
 * se lista domena ne prepisuje na dva mesta.
 */
export function listModelScopes(): Promise<{ scopes: ModelScopeDto[] }> {
  return getJson<{ scopes: ModelScopeDto[] }>("/api/v1/core/ai/models/scopes");
}

/** Svi modeli sa odlukom za traženi opseg. */
export function listCoreModels(
  scope = "global",
  onlyEnabled = false,
): Promise<{ models: CatalogModel[] }> {
  const upit = onlyEnabled ? "&only_enabled=true" : "";
  return getJson<{ models: CatalogModel[] }>(
    `/api/v1/core/ai/models?scope=${encodeURIComponent(scope)}${upit}`,
  );
}

/** Uključuje ili isključuje model za sve domene. */
export function setCoreModelEnabled(payload: {
  provider: string;
  model: string;
  enabled: boolean;
  scope?: string;
}): Promise<{ provider: string; model: string; enabled: boolean }> {
  return putJson<
    { provider: string; model: string; enabled: boolean },
    typeof payload
  >("/api/v1/core/ai/models/enabled", payload);
}


// ==========          CORE ASISTENT (sistemski chat)          ==========

export type CorePersona = {
  id: string;
  name: string;
  /** „global" ili domen — po njemu se zna gde se izmena teksta upisuje. */
  scope: string;
  /** True kad je tekst persone izmenjen u odnosu na ugrađeni. */
  customized: boolean;
};

/** Persona sa celim .md tekstom (za uređivanje). */
export type PersonaDoc = CorePersona & { markdown: string };

export type CoreChatTurn = { author: "me" | "assistant"; text: string };

export type CoreAnswer = {
  reply: string;
  persona: string;
  model: string;
  provider: string;
  source: string;
  is_fallback: boolean;
  sources: string[];
  prompt_tokens: number;
  output_tokens: number;
  duration_ms: number;
  cost_usd: number;
};

/** Persone dostupne u opsegu: globalne, pa persone tog opsega. */
export function listCorePersonas(
  scope = "core",
): Promise<{ personas: CorePersona[] }> {
  return getJson<{ personas: CorePersona[] }>(
    `/api/v1/core/ai/personas?scope=${encodeURIComponent(scope)}`,
  );
}

function personaPath(scope: string, id: string): string {
  return `/api/v1/core/ai/personas/${encodeURIComponent(scope)}/${encodeURIComponent(id)}`;
}

/** Tekst persone (.md) za uređivanje. */
export function readPersona(scope: string, id: string): Promise<PersonaDoc> {
  return getJson<PersonaDoc>(personaPath(scope, id));
}

/** Upisuje izmenjeni tekst persone; važi od sledeće poruke. */
export function savePersona(
  scope: string,
  id: string,
  markdown: string,
): Promise<PersonaDoc> {
  return putJson<PersonaDoc, { markdown: string }>(personaPath(scope, id), {
    markdown,
  });
}

/** Vraća personu na ugrađeni tekst. */
export function resetPersona(scope: string, id: string): Promise<PersonaDoc> {
  return deleteRequest<PersonaDoc>(personaPath(scope, id));
}

/** Pitanje CORE asistentu. `scope` bira personu (npr. „filmium" → njen agent). */
export function askCore(payload: {
  persona: string;
  message: string;
  history: CoreChatTurn[];
  model?: string;
  provider?: string;
  scope?: string;
}): Promise<CoreAnswer> {
  return postJson<CoreAnswer, typeof payload>("/api/v1/core/ai/ask", payload);
}


// ==========          ĆELIJE (odcepljeni domeni preko API-ja)          ==========

export type CellProbe = {
  domain_id: string;
  address: string;
  online: boolean;
  /** `/cell/status` telo kad je online (ime, verzija, port…), inače null. */
  status: Record<string, unknown> | null;
  reason: string;
};

/** Skenira ćeliju jednog domena po zabeleženoj adresi (CORE → ćelija). */
export function scanCell(domainId: string): Promise<CellProbe> {
  return getJson<CellProbe>(`/api/v1/cells/${encodeURIComponent(domainId)}`);
}

/** Skenira sve zabeležene ćelije. */
export function scanCells(): Promise<{ cells: CellProbe[] }> {
  return getJson<{ cells: CellProbe[] }>("/api/v1/cells");
}

/** Diže ćeliju u tihom modu (ako nije online) i vraća njeno stanje. */
export function launchCell(domainId: string): Promise<CellProbe> {
  return postJson<CellProbe, Record<string, never>>(
    `/api/v1/cells/${encodeURIComponent(domainId)}/launch`,
    {},
  );
}
