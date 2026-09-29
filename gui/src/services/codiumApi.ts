import {
  deleteRequest,
  getJson,
  patchJson,
  postJson,
  putJson,
} from "./httpClient";

import type {
  ActivityResponse,
  AgendaResponse,
  AgentPatch,
  AgentRunResponse,
  AgentRunStarted,
  AgentRunsResponse,
  AgentRunSummary,
  AgentsResponse,
  AgentSummary,
  AgentToolsResponse,
  AlertRule,
  AlertRuleCreateRequest,
  AlertRulesResponse,
  AlertsResponse,
  AnalyticsReport,
  AnalyticsSummaryResponse,
  Approval,
  AutomationActionsResponse,
  AutomationEventsResponse,
  AutomationRule,
  AutomationRuleCreateRequest,
  AutomationRulesResponse,
  AutomationRuleUpdateRequest,
  AutomationRunsResponse,
  AutomationTestResponse,
  ApprovalsResponse,
  AuditLogResponse,
  BranchesResponse,
  BrainFileContent,
  BrainInfo,
  CancelResponse,
  Client,
  DevServerStatus,
  ClientCreateRequest,
  ClientsResponse,
  CommitsResponse,
  DeployableRunsResponse,
  DeployHealth,
  Deployment,
  DeploymentsResponse,
  DeployTarget,
  DeployTargetCreateRequest,
  DeployTargetsResponse,
  DeployTargetUpdateRequest,
  DevlogIndex,
  DiffResponse,
  InfraDiscoverResponse,
  InfraLogsResponse,
  InfraNodesResponse,
  InfraService,
  InfraServiceCreateRequest,
  InfraServicesResponse,
  InfraServiceStatus,
  MetricSeriesResponse,
  MonitoringOverviewResponse,
  FileAtResponse,
  FileContent,
  FileListResponse,
  FileNode,
  Note,
  NoteCreateRequest,
  NotesResponse,
  Pipeline,
  PipelineCreateRequest,
  PipelinesResponse,
  PipelineRun,
  PipelineUpdateRequest,
  Project,
  ProjectCreateRequest,
  ProjectsResponse,
  ProjectUpdateRequest,
  ProjectVisibility,
  ReportsListResponse,
  RepositoriesResponse,
  Repository,
  RepositoryCreateRequest,
  RepoStatus,
  RunDetailResponse,
  RunLogsResponse,
  RunsResponse,
  ScopeRule,
  ScopeRuleRequest,
  ScopeRulesResponse,
  SuggestionsResponse,
  SyncResponse,
  Task,
  TaskCreateRequest,
  TasksResponse,
  TaskUpdateRequest,
} from "../types/codium";


// ==========          PROJEKTI          ==========

/** Svi projekti; opciono filtrirani po vidljivosti (client|private). */
export function getProjects(
  visibility?: ProjectVisibility,
): Promise<ProjectsResponse> {
  const query = visibility ? `?visibility=${visibility}` : "";
  return getJson<ProjectsResponse>(`/api/v1/codium/projects${query}`);
}

/** Jedan projekat po ID-u. */
export function getProject(projectId: number): Promise<Project> {
  return getJson<Project>(`/api/v1/codium/projects/${projectId}`);
}

/** Dodaje nov projekat (slug se izvodi iz imena ako nije zadat). */
export function createProject(
  project: ProjectCreateRequest,
): Promise<Project> {
  return postJson<Project, ProjectCreateRequest>(
    "/api/v1/codium/projects",
    project,
  );
}

/** Menja projekat (delimično). */
export function updateProject(
  projectId: number,
  change: ProjectUpdateRequest,
): Promise<Project> {
  return patchJson<Project, ProjectUpdateRequest>(
    `/api/v1/codium/projects/${projectId}`,
    change,
  );
}


// ==========          KLIJENTI          ==========

/** Svi klijenti. */
export function getClients(): Promise<ClientsResponse> {
  return getJson<ClientsResponse>("/api/v1/codium/clients");
}

/** Dodaje novog klijenta. */
export function createClient(
  client: ClientCreateRequest,
): Promise<Client> {
  return postJson<Client, ClientCreateRequest>(
    "/api/v1/codium/clients",
    client,
  );
}


// ==========          TASKOVI          ==========

/** Taskovi; opciono filtrirani po projektu. */
export function getTasks(projectId?: number): Promise<TasksResponse> {
  const query = projectId != null ? `?project_id=${projectId}` : "";
  return getJson<TasksResponse>(`/api/v1/codium/tasks${query}`);
}

/** Dodaje nov task. */
export function createTask(task: TaskCreateRequest): Promise<Task> {
  return postJson<Task, TaskCreateRequest>("/api/v1/codium/tasks", task);
}

/** Menja task (delimično). */
export function updateTask(
  taskId: number,
  change: TaskUpdateRequest,
): Promise<Task> {
  return patchJson<Task, TaskUpdateRequest>(
    `/api/v1/codium/tasks/${taskId}`,
    change,
  );
}


// ==========          BELEŠKE          ==========

/** Beleške; po projektu, ili globalni inbox (inboxOnly=true). */
export function getNotes(
  projectId?: number,
  inboxOnly = false,
): Promise<NotesResponse> {
  const params = new URLSearchParams();
  if (projectId != null) {
    params.set("project_id", String(projectId));
  }
  if (inboxOnly) {
    params.set("inbox_only", "true");
  }
  const query = params.toString() ? `?${params.toString()}` : "";
  return getJson<NotesResponse>(`/api/v1/codium/notes${query}`);
}

/** Dodaje belešku (aktivni projekat opcion → auto project_id/client_id). */
export function createNote(note: NoteCreateRequest): Promise<Note> {
  return postJson<Note, NoteCreateRequest>("/api/v1/codium/notes", note);
}


// ==========          DEV SERVER (lokalni host)          ==========

/** Pokreće lokalni dev server projekta (komanda + local_path iz baze). */
export function startDevServer(projectId: number): Promise<DevServerStatus> {
  return postJson<DevServerStatus, Record<string, never>>(
    `/api/v1/codium/projects/${projectId}/dev/start`,
    {},
  );
}

/** Gasi lokalni dev server projekta. */
export function stopDevServer(projectId: number): Promise<DevServerStatus> {
  return postJson<DevServerStatus, Record<string, never>>(
    `/api/v1/codium/projects/${projectId}/dev/stop`,
    {},
  );
}

/** Stanje lokalnog dev servera projekta. */
export function getDevServerStatus(
  projectId: number,
): Promise<DevServerStatus> {
  return getJson<DevServerStatus>(
    `/api/v1/codium/projects/${projectId}/dev/status`,
  );
}


// ==========          AGENDA (rokovi + podsetnici)          ==========

/**
 * Objedinjena agenda: rokovi taskova, podsetnici beleški i rokovi projekata
 * u narednih `daysAhead` dana; `includeOverdue` dodaje probijene rokove;
 * `projectId` sužava na jedan projekat.
 */
export function getAgenda(options?: {
  daysAhead?: number;
  includeOverdue?: boolean;
  projectId?: number;
}): Promise<AgendaResponse> {
  const params = new URLSearchParams();
  if (options?.daysAhead != null) {
    params.set("days_ahead", String(options.daysAhead));
  }
  if (options?.includeOverdue === false) {
    params.set("include_overdue", "false");
  }
  if (options?.projectId != null) {
    params.set("project_id", String(options.projectId));
  }
  const query = params.toString() ? `?${params.toString()}` : "";
  return getJson<AgendaResponse>(`/api/v1/codium/agenda${query}`);
}


// ==========          PROJECT BRAIN (.codium/)          ==========

/** Stanje `.codium/` foldera projekta. */
export function getBrain(projectId: number): Promise<BrainInfo> {
  return getJson<BrainInfo>(`/api/v1/codium/projects/${projectId}/brain`);
}

/** Generiše skelet `.codium/` foldera (ne prepisuje postojeće). */
export function generateBrain(projectId: number): Promise<BrainInfo> {
  return postJson<BrainInfo, Record<string, never>>(
    `/api/v1/codium/projects/${projectId}/brain`,
    {},
  );
}

/** Sadržaj jednog brain fajla (read-only). */
export function getBrainFile(
  projectId: number,
  name: string,
): Promise<BrainFileContent> {
  return getJson<BrainFileContent>(
    `/api/v1/codium/projects/${projectId}/brain/file?name=${encodeURIComponent(name)}`,
  );
}

/** Sadržaj `dev-log/INDEX.md` projekta. */
export function getBrainDevlog(projectId: number): Promise<DevlogIndex> {
  return getJson<DevlogIndex>(
    `/api/v1/codium/projects/${projectId}/brain/devlog`,
  );
}


// ==========          EXPLORER (file tree)          ==========

/** Listing jednog nivoa fajl-stabla projekta. */
export function listFiles(
  projectId: number,
  path = "",
): Promise<FileListResponse> {
  const query = path ? `?path=${encodeURIComponent(path)}` : "";
  return getJson<FileListResponse>(
    `/api/v1/codium/projects/${projectId}/files${query}`,
  );
}

/** Sadržaj tekstualnog fajla. */
export function readFileContent(
  projectId: number,
  path: string,
): Promise<FileContent> {
  return getJson<FileContent>(
    `/api/v1/codium/projects/${projectId}/files/content?path=${encodeURIComponent(path)}`,
  );
}

/** Pravi fajl ili folder u stablu projekta. */
export function createFileNode(
  projectId: number,
  path: string,
  kind: "file" | "dir",
): Promise<FileNode> {
  return postJson<FileNode, { path: string; kind: string }>(
    `/api/v1/codium/projects/${projectId}/files`,
    { path, kind },
  );
}

/** Upisuje sadržaj u postojeći fajl (Save iz editora). */
export function writeFileContent(
  projectId: number,
  path: string,
  content: string,
): Promise<FileNode> {
  return putJson<FileNode, { path: string; content: string }>(
    `/api/v1/codium/projects/${projectId}/files/content`,
    { path, content },
  );
}

/** Preimenuje fajl/folder (samo ime). */
export function renameFileNode(
  projectId: number,
  path: string,
  newName: string,
): Promise<FileNode> {
  return patchJson<FileNode, { path: string; new_name: string }>(
    `/api/v1/codium/projects/${projectId}/files`,
    { path, new_name: newName },
  );
}

/** Briše fajl ili (rekurzivno) folder. */
export function deleteFileNode(
  projectId: number,
  path: string,
): Promise<void> {
  return deleteRequest<void>(
    `/api/v1/codium/projects/${projectId}/files?path=${encodeURIComponent(path)}`,
  );
}

/** Kopira fajl/folder u ciljni folder (Copy → Paste). */
export function copyFileNode(
  projectId: number,
  path: string,
  destDir: string,
): Promise<FileNode> {
  return postJson<FileNode, { path: string; dest_dir: string }>(
    `/api/v1/codium/projects/${projectId}/files/copy`,
    { path, dest_dir: destDir },
  );
}

/** Premešta fajl/folder u ciljni folder (Cut → Paste). */
export function moveFileNode(
  projectId: number,
  path: string,
  destDir: string,
): Promise<FileNode> {
  return postJson<FileNode, { path: string; dest_dir: string }>(
    `/api/v1/codium/projects/${projectId}/files/move`,
    { path, dest_dir: destDir },
  );
}

/** Otvara stavku u sistemskom fajl-menadžeru (Open in explorer). */
export function revealFileNode(
  projectId: number,
  path: string,
): Promise<void> {
  return postJson<void, { path: string }>(
    `/api/v1/codium/projects/${projectId}/files/reveal`,
    { path },
  );
}


// ==========          AI ASISTENT (F9)          ==========

export type AssistantPersona = { id: string; name: string };

export type AssistantChatTurn = { author: "me" | "assistant"; text: string };

export type AssistantAnswer = {
  reply: string;
  persona: string;
  model: string;
  is_fallback: boolean;
  sources: string[];
  provider: string;
  source: string;
  // Merenja poziva; GUI ih prikazuje kao trošak ispod odgovora.
  prompt_tokens: number;
  output_tokens: number;
  duration_ms: number;
  cost_usd: number;
};

/** Raspoložive persone (chat modovi) asistenta. */
export function listAssistantPersonas(): Promise<{ personas: AssistantPersona[] }> {
  return getJson<{ personas: AssistantPersona[] }>("/api/v1/codium/ai/personas");
}

/** Postavi pitanje asistentu (persona + kontekst projekta + istorija). */
export function askAssistant(payload: {
  project_id: number | null;
  persona: string;
  message: string;
  history: AssistantChatTurn[];
  model?: string;
  provider?: string;
}): Promise<AssistantAnswer> {
  return postJson<AssistantAnswer, typeof payload>(
    "/api/v1/codium/ai/ask",
    payload,
  );
}

// Tip modela se ne definiše ponovo — CatalogModel iz Task 9 je jedini opis
// tog oblika. Uvoz tipa se briše pri prevođenju, pa ne pravi zavisnost u
// izvršnom kodu.
import type { CatalogModel } from "../features/codium/modelPicker";

export type { CatalogModel };

export type ModelPrefDto = {
  project_id: number | null;
  persona: string;
  model: string;
  provider: string;
};

/** Katalog modela (lokalni + online) dostupnih asistentu.
 *
 * `onlyEnabled` je za chat izbornik: katalog sa 300+ modela ne treba da
 * putuje ceo da bi se prikazalo pet. Podešavanja ga zovu bez toga, jer
 * moraju da vide i isključene da bi mogli da ih vrate.
 */
export function listAssistantModels(
  onlyEnabled = false,
): Promise<{ models: CatalogModel[] }> {
  const upit = onlyEnabled ? "?only_enabled=true" : "";
  return getJson<{ models: CatalogModel[] }>(
    `/api/v1/codium/ai/models${upit}`,
  );
}

/** Uključuje ili isključuje model za chat izbornik. */
export function setModelEnabled(payload: {
  provider: string;
  model: string;
  enabled: boolean;
}): Promise<{ provider: string; model: string; enabled: boolean }> {
  return putJson<
    { provider: string; model: string; enabled: boolean },
    typeof payload
  >("/api/v1/codium/ai/models/enabled", payload);
}

/** Zapamćen izbor modela za par (projekat, persona), ako postoji. */
export function getModelPref(
  projectId: number | null,
  persona: string,
): Promise<{ pref: ModelPrefDto | null }> {
  const query = new URLSearchParams({ persona });
  if (projectId !== null) {
    query.set("project_id", String(projectId));
  }
  return getJson<{ pref: ModelPrefDto | null }>(
    `/api/v1/codium/ai/prefs?${query.toString()}`,
  );
}

/** Pamti izbor modela za par (projekat, persona). */
/**
 * Vraća par (projekat, persona) na podrazumevani model brisanjem postavke.
 * Bez ovoga zapamćen model i dalje pobeđuje registar u ruteru, pa bi izbornik
 * pokazivao „Podrazumevani model" a odgovarao bi zapamćeni.
 */
export function clearModelPref(
  projectId: number | null,
  persona: string,
): Promise<{ pref: ModelPrefDto | null }> {
  const query = new URLSearchParams({ persona });
  if (projectId !== null) {
    query.set("project_id", String(projectId));
  }
  return deleteRequest<{ pref: ModelPrefDto | null }>(
    `/api/v1/codium/ai/prefs?${query.toString()}`,
  );
}

export function setModelPref(payload: {
  project_id: number | null;
  persona: string;
  model: string;
  provider: string;
}): Promise<{ pref: ModelPrefDto }> {
  return putJson<{ pref: ModelPrefDto }, typeof payload>(
    "/api/v1/codium/ai/prefs",
    payload,
  );
}


/** Zbir potrošnje (period: "day" | "month"; bez njega — celo vreme). */
export function getUsageSummary(params?: {
  period?: "day" | "month";
  projectId?: number | null;
}): Promise<{
  calls: number;
  prompt_tokens: number;
  output_tokens: number;
  cost_usd: number;
}> {
  const query = new URLSearchParams();
  if (params?.period) {
    query.set("period", params.period);
  }
  if (params?.projectId !== undefined && params.projectId !== null) {
    query.set("project_id", String(params.projectId));
  }
  const suffix = query.toString() === "" ? "" : `?${query.toString()}`;
  return getJson(`/api/v1/codium/ai/usage${suffix}`);
}


// ==========          DNEVNIK I AKTIVNOST          ==========

/** Poslednja dešavanja: pozivi modela i odbijene akcije, u jednoj liniji. */
export function getActivity(limit = 20): Promise<ActivityResponse> {
  return getJson(`/api/v1/codium/audit/activity?limit=${limit}`);
}


// ==========          DOZVOLE I ODOBRENJA          ==========

export function getScopeRules(): Promise<ScopeRulesResponse> {
  return getJson("/api/v1/codium/audit/rules");
}

export function addScopeRule(rule: ScopeRuleRequest): Promise<ScopeRule> {
  return postJson("/api/v1/codium/audit/rules", rule);
}

export function deleteScopeRule(ruleId: number): Promise<{ ok: boolean }> {
  return deleteRequest(`/api/v1/codium/audit/rules/${ruleId}`);
}

export function getApprovals(): Promise<ApprovalsResponse> {
  return getJson("/api/v1/codium/audit/approvals");
}

export function approveRequest(id: number, note = ""): Promise<Approval> {
  return postJson(`/api/v1/codium/audit/approvals/${id}/approve`, { note });
}

export function rejectRequest(id: number, note = ""): Promise<Approval> {
  return postJson(`/api/v1/codium/audit/approvals/${id}/reject`, { note });
}

// ==========          DNEVNIK          ==========

export function getAuditLog(
  params: { actor?: string; action?: string; limit?: number; offset?: number } = {},
): Promise<AuditLogResponse> {
  const upit = new URLSearchParams();
  if (params.actor) upit.set("actor", params.actor);
  if (params.action) upit.set("action", params.action);
  upit.set("limit", String(params.limit ?? 50));
  upit.set("offset", String(params.offset ?? 0));
  return getJson(`/api/v1/codium/audit/log?${upit.toString()}`);
}

// ==========          AGENTI          ==========

export function getAgents(): Promise<AgentsResponse> {
  return getJson("/api/v1/codium/agents/");
}

export function updateAgent(
  agentId: number,
  change: AgentPatch,
): Promise<AgentSummary> {
  return patchJson(`/api/v1/codium/agents/${agentId}`, change);
}

export function getAgentTools(): Promise<AgentToolsResponse> {
  return getJson("/api/v1/codium/agents/tools");
}

export function startAgentRun(
  agentId: number,
  task: string,
  projectId: number | null = null,
): Promise<AgentRunStarted> {
  return postJson(`/api/v1/codium/agents/${agentId}/run`, {
    task,
    project_id: projectId,
  });
}

export function getAgentRun(
  runId: number,
  sinceIdx = -1,
): Promise<AgentRunResponse> {
  return getJson(
    `/api/v1/codium/agents/runs/${runId}?since_idx=${sinceIdx}`,
  );
}

export function getAgentRuns(limit = 20): Promise<AgentRunsResponse> {
  return getJson(`/api/v1/codium/agents/runs?limit=${limit}`);
}

export function cancelAgentRun(runId: number): Promise<AgentRunSummary> {
  return postJson(`/api/v1/codium/agents/runs/${runId}/cancel`, {});
}

// ==========          REPOZITORIJUMI (E2)          ==========

export function fetchRepositories(
  projectId?: number,
): Promise<RepositoriesResponse> {
  const upit = projectId === undefined ? "" : `?project_id=${projectId}`;
  return getJson(`/api/v1/codium/repositories/${upit}`);
}

export function fetchRepoSuggestions(): Promise<SuggestionsResponse> {
  return getJson("/api/v1/codium/repositories/suggestions");
}

export function registerRepository(
  zahtev: RepositoryCreateRequest,
): Promise<Repository> {
  return postJson("/api/v1/codium/repositories/", zahtev);
}

export function deleteRepository(repoId: number): Promise<{ deleted: number }> {
  return deleteRequest(`/api/v1/codium/repositories/${repoId}`);
}

export function fetchRepoStatus(repoId: number): Promise<RepoStatus> {
  return getJson(`/api/v1/codium/repositories/${repoId}/status`);
}

export function fetchRepoBranches(repoId: number): Promise<BranchesResponse> {
  return getJson(`/api/v1/codium/repositories/${repoId}/branches`);
}

export function fetchRepoCommits(
  repoId: number,
  branch = "",
  limit = 50,
  offset = 0,
): Promise<CommitsResponse> {
  const grana = branch ? `&branch=${encodeURIComponent(branch)}` : "";
  return getJson(
    `/api/v1/codium/repositories/${repoId}/commits?limit=${limit}&offset=${offset}${grana}`,
  );
}

export function fetchRepoDiff(
  repoId: number,
  a: string,
  b: string,
  path?: string,
): Promise<DiffResponse> {
  const putanja = path ? `&path=${encodeURIComponent(path)}` : "";
  return getJson(
    `/api/v1/codium/repositories/${repoId}/diff?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}${putanja}`,
  );
}

export function fetchRepoFileAt(
  repoId: number,
  ref: string,
  path: string,
): Promise<FileAtResponse> {
  return getJson(
    `/api/v1/codium/repositories/${repoId}/file?ref=${encodeURIComponent(ref)}&path=${encodeURIComponent(path)}`,
  );
}

export function syncRepository(repoId: number): Promise<SyncResponse> {
  return postJson(`/api/v1/codium/repositories/${repoId}/sync`, {});
}

// ==========          PIPELINE-I (E3)          ==========

export function fetchPipelines(repositoryId?: number): Promise<PipelinesResponse> {
  const upit = repositoryId === undefined ? "" : `?repository_id=${repositoryId}`;
  return getJson(`/api/v1/codium/pipelines/${upit}`);
}

export function createPipeline(zahtev: PipelineCreateRequest): Promise<Pipeline> {
  return postJson("/api/v1/codium/pipelines/", zahtev);
}

export function updatePipeline(
  pipelineId: number,
  zahtev: PipelineUpdateRequest,
): Promise<Pipeline> {
  return putJson(`/api/v1/codium/pipelines/${pipelineId}`, zahtev);
}

export function deletePipeline(pipelineId: number): Promise<{ deleted: number }> {
  return deleteRequest(`/api/v1/codium/pipelines/${pipelineId}`);
}

export function runPipeline(pipelineId: number): Promise<PipelineRun> {
  return postJson(`/api/v1/codium/pipelines/${pipelineId}/run`, {});
}

export function fetchRuns(
  pipelineId?: number,
  limit = 50,
): Promise<RunsResponse> {
  const filter = pipelineId === undefined ? "" : `&pipeline_id=${pipelineId}`;
  return getJson(`/api/v1/codium/pipelines/runs?limit=${limit}${filter}`);
}

export function fetchRunDetail(runId: number): Promise<RunDetailResponse> {
  return getJson(`/api/v1/codium/pipelines/runs/${runId}`);
}

export function fetchRunLogs(
  runId: number,
  afterSeq = 0,
): Promise<RunLogsResponse> {
  return getJson(
    `/api/v1/codium/pipelines/runs/${runId}/logs?after_seq=${afterSeq}`,
  );
}

export function cancelRun(runId: number): Promise<CancelResponse> {
  return postJson(`/api/v1/codium/pipelines/runs/${runId}/cancel`, {});
}

// ==========          ISPORUKA (E4)          ==========

export function fetchDeployTargets(
  projectId?: number,
): Promise<DeployTargetsResponse> {
  const upit = projectId === undefined ? "" : `?project_id=${projectId}`;
  return getJson(`/api/v1/codium/deployments/targets${upit}`);
}

export function createDeployTarget(
  zahtev: DeployTargetCreateRequest,
): Promise<DeployTarget> {
  return postJson("/api/v1/codium/deployments/targets", zahtev);
}

export function updateDeployTarget(
  targetId: number,
  zahtev: DeployTargetUpdateRequest,
): Promise<DeployTarget> {
  return patchJson(`/api/v1/codium/deployments/targets/${targetId}`, zahtev);
}

export function deleteDeployTarget(
  targetId: number,
): Promise<{ deleted: boolean }> {
  return deleteRequest(`/api/v1/codium/deployments/targets/${targetId}`);
}

export function fetchDeployHealth(targetId: number): Promise<DeployHealth> {
  return getJson(`/api/v1/codium/deployments/targets/${targetId}/health`);
}

/** Pokretanja koja stvarno imaju paket — samo njih ekran nudi pod „Isporuči". */
export function fetchDeployableRuns(
  limit = 30,
): Promise<DeployableRunsResponse> {
  return getJson(`/api/v1/codium/deployments/runs?limit=${limit}`);
}

export function fetchDeployments(
  targetId?: number,
  limit = 50,
): Promise<DeploymentsResponse> {
  const filter = targetId === undefined ? "" : `&target_id=${targetId}`;
  return getJson(`/api/v1/codium/deployments/?limit=${limit}${filter}`);
}

export function deployRun(
  targetId: number,
  runId: number,
): Promise<Deployment> {
  return postJson("/api/v1/codium/deployments/", {
    target_id: targetId,
    run_id: runId,
  });
}

export function rollbackDeployment(
  deploymentId: number,
): Promise<Deployment> {
  return postJson(`/api/v1/codium/deployments/${deploymentId}/rollback`, {});
}

// ==========          INFRASTRUKTURA (E5)          ==========

export function fetchInfraNodes(): Promise<InfraNodesResponse> {
  return getJson("/api/v1/codium/infrastructure/nodes");
}

export function fetchInfraServices(
  nodeId?: number,
  projectId?: number,
): Promise<InfraServicesResponse> {
  const delovi: string[] = [];
  if (nodeId !== undefined) {
    delovi.push(`node_id=${nodeId}`);
  }
  if (projectId !== undefined) {
    delovi.push(`project_id=${projectId}`);
  }
  const upit = delovi.length > 0 ? `?${delovi.join("&")}` : "";
  return getJson(`/api/v1/codium/infrastructure/services${upit}`);
}

export function createInfraService(
  zahtev: InfraServiceCreateRequest,
): Promise<InfraService> {
  return postJson("/api/v1/codium/infrastructure/services", zahtev);
}

export function deleteInfraService(
  serviceId: number,
): Promise<{ deleted: boolean }> {
  return deleteRequest(`/api/v1/codium/infrastructure/services/${serviceId}`);
}

/** Predlog nađenih servisa. Ne upisuje ništa — čovek bira šta ulazi. */
export function discoverInfraServices(
  nodeId: number,
): Promise<InfraDiscoverResponse> {
  return postJson(
    `/api/v1/codium/infrastructure/nodes/${nodeId}/discover`,
    {},
  );
}

export function startInfraService(
  serviceId: number,
): Promise<InfraServiceStatus> {
  return postJson(
    `/api/v1/codium/infrastructure/services/${serviceId}/start`,
    {},
  );
}

export function stopInfraService(
  serviceId: number,
): Promise<InfraServiceStatus> {
  return postJson(
    `/api/v1/codium/infrastructure/services/${serviceId}/stop`,
    {},
  );
}

export function restartInfraService(
  serviceId: number,
): Promise<InfraServiceStatus> {
  return postJson(
    `/api/v1/codium/infrastructure/services/${serviceId}/restart`,
    {},
  );
}

export function fetchInfraLogs(
  serviceId: number,
  lines = 200,
): Promise<InfraLogsResponse> {
  return getJson(
    `/api/v1/codium/infrastructure/services/${serviceId}/logs?lines=${lines}`,
  );
}

// ==========          MERENJE (E6)          ==========

export function fetchMonitoringOverview(): Promise<MonitoringOverviewResponse> {
  return getJson("/api/v1/codium/monitoring/overview");
}

/** Već sažete kante — grafikon ne dobija hiljade tačaka. */
export function fetchMetricSeries(
  serviceId: number,
  metric: string,
  bucket = "hour",
  limit = 200,
): Promise<MetricSeriesResponse> {
  return getJson(
    `/api/v1/codium/monitoring/series?service_id=${serviceId}` +
      `&metric=${encodeURIComponent(metric)}&bucket=${bucket}&limit=${limit}`,
  );
}

export function collectMetricsNow(): Promise<{ samples: number }> {
  return postJson("/api/v1/codium/monitoring/collect", {});
}

export function fetchAlertRules(
  serviceId?: number,
): Promise<AlertRulesResponse> {
  const upit = serviceId === undefined ? "" : `?service_id=${serviceId}`;
  return getJson(`/api/v1/codium/monitoring/rules${upit}`);
}

export function createAlertRule(
  zahtev: AlertRuleCreateRequest,
): Promise<AlertRule> {
  return postJson("/api/v1/codium/monitoring/rules", zahtev);
}

export function deleteAlertRule(
  ruleId: number,
): Promise<{ deleted: boolean }> {
  return deleteRequest(`/api/v1/codium/monitoring/rules/${ruleId}`);
}

export function fetchAlerts(
  state?: string,
  limit = 50,
): Promise<AlertsResponse> {
  const filter = state === undefined ? "" : `&state=${state}`;
  return getJson(`/api/v1/codium/monitoring/alerts?limit=${limit}${filter}`);
}

// ==========          IZVEŠTAJI (E7)          ==========

export function fetchReportList(): Promise<ReportsListResponse> {
  return getJson("/api/v1/codium/analytics/reports");
}

export function fetchAnalyticsSummary(
  period = "30d",
): Promise<AnalyticsSummaryResponse> {
  return getJson(`/api/v1/codium/analytics/summary?period=${period}`);
}

export function fetchReport(
  name: string,
  period = "30d",
  projectId?: number,
): Promise<AnalyticsReport> {
  const filter = projectId === undefined ? "" : `&project_id=${projectId}`;
  return getJson(
    `/api/v1/codium/analytics/reports/${encodeURIComponent(name)}` +
      `?period=${period}${filter}`,
  );
}

/** Putanja CSV izvoza. Ne dohvata se — otvara se u pregledaču. */
export function reportExportUrl(name: string, period = "30d"): string {
  return `/api/v1/codium/analytics/export/${encodeURIComponent(name)}?period=${period}`;
}

// ==========          AUTOMATIZACIJA (E10)          ==========

export function fetchAutomationEvents(): Promise<AutomationEventsResponse> {
  return getJson("/api/v1/codium/automations/events");
}

export function fetchAutomationActions(): Promise<AutomationActionsResponse> {
  return getJson("/api/v1/codium/automations/actions");
}

export function fetchAutomationRules(): Promise<AutomationRulesResponse> {
  return getJson("/api/v1/codium/automations/");
}

export function createAutomationRule(
  zahtev: AutomationRuleCreateRequest,
): Promise<AutomationRule> {
  return postJson("/api/v1/codium/automations/", zahtev);
}

export function updateAutomationRule(
  ruleId: number,
  zahtev: AutomationRuleUpdateRequest,
): Promise<AutomationRule> {
  return patchJson(`/api/v1/codium/automations/${ruleId}`, zahtev);
}

export function deleteAutomationRule(
  ruleId: number,
): Promise<{ deleted: boolean }> {
  return deleteRequest(`/api/v1/codium/automations/${ruleId}`);
}

/** Proba nad izmišljenim događajem. NE izvršava akcije. */
export function testAutomationRule(
  ruleId: number,
  payload: Record<string, unknown>,
): Promise<AutomationTestResponse> {
  return postJson(`/api/v1/codium/automations/${ruleId}/test`, { payload });
}

export function fetchAutomationRuns(
  ruleId?: number,
  limit = 50,
): Promise<AutomationRunsResponse> {
  const filter = ruleId === undefined ? "" : `&rule_id=${ruleId}`;
  return getJson(`/api/v1/codium/automations/runs?limit=${limit}${filter}`);
}
