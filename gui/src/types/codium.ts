// ==========          TIPOVI: CODIUM (razvoj softvera)          ==========

export type ProjectVisibility = "client" | "private";

export type ProjectStatus = "active" | "paused" | "done" | "archived";

export type TaskStatus = "todo" | "in_progress" | "done" | "blocked";

export type Priority = "low" | "normal" | "high" | "urgent";

export type NoteSource =
  | "manual"
  | "chat"
  | "ai"
  | "email"
  | "preview"
  | "task"
  | "roadmap"
  | "meeting";

export type NoteImportance = "low" | "normal" | "high" | "urgent";

export type NoteStatus = "active" | "done" | "archived";


// ---------- PROJEKAT ----------

export interface Project {
  id: number;
  name: string;
  slug: string;
  type: string;
  visibility: ProjectVisibility;
  status: ProjectStatus;
  local_path: string | null;
  project_brain_path: string | null;
  client_id: number | null;
  repository_url: string | null;
  live_url: string | null;
  staging_url: string | null;
  preview_url: string | null;
  stack: string;
  priority: Priority;
  dev_command: string;
  dev_port: number | null;
  started_at: string | null;
  deadline_at: string | null;
  last_opened_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DevServerStatus {
  project_id: number;
  running: boolean;
  pid: number | null;
  command: string | null;
  preview_url: string | null;
}

export interface ProjectsResponse {
  count: number;
  projects: Project[];
}

export interface ProjectCreateRequest {
  name: string;
  type?: string;
  visibility?: ProjectVisibility;
  client_id?: number | null;
  local_path?: string | null;
  repository_url?: string | null;
  stack?: string;
  priority?: Priority;
  deadline_at?: string | null;
  dev_command?: string;
  dev_port?: number | null;
  preview_url?: string | null;
  slug?: string | null;
}

export interface ProjectUpdateRequest {
  name?: string;
  type?: string;
  visibility?: ProjectVisibility;
  status?: ProjectStatus;
  client_id?: number | null;
  local_path?: string | null;
  project_brain_path?: string | null;
  repository_url?: string | null;
  live_url?: string | null;
  staging_url?: string | null;
  preview_url?: string | null;
  stack?: string;
  priority?: Priority;
  dev_command?: string;
  dev_port?: number | null;
  started_at?: string | null;
  deadline_at?: string | null;
  last_opened_at?: string | null;
}


// ---------- KLIJENT ----------

export interface Client {
  id: number;
  name: string;
  company_name: string;
  type: string;
  email: string | null;
  phone: string | null;
  website: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface ClientsResponse {
  count: number;
  clients: Client[];
}

export interface ClientCreateRequest {
  name: string;
  company_name?: string;
  type?: string;
  email?: string | null;
  phone?: string | null;
  website?: string | null;
  notes?: string;
}


// ---------- TASK ----------

export interface Task {
  id: number;
  project_id: number | null;
  title: string;
  description: string;
  status: TaskStatus;
  priority: Priority;
  due_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TasksResponse {
  count: number;
  tasks: Task[];
}

export interface TaskCreateRequest {
  title: string;
  project_id?: number | null;
  description?: string;
  priority?: Priority;
  due_at?: string | null;
}

export interface TaskUpdateRequest {
  title?: string;
  project_id?: number | null;
  description?: string;
  status?: TaskStatus;
  priority?: Priority;
  due_at?: string | null;
  completed_at?: string | null;
}


// ---------- BELEŠKA ----------

export interface Note {
  id: number;
  project_id: number | null;
  client_id: number | null;
  title: string;
  body: string;
  source: NoteSource;
  importance: NoteImportance;
  tags: string;
  reminder_at: string | null;
  status: NoteStatus;
  created_at: string;
  updated_at: string;
}

export interface NotesResponse {
  count: number;
  notes: Note[];
}

export interface NoteCreateRequest {
  title: string;
  body?: string;
  project_id?: number | null;
  client_id?: number | null;
  source?: NoteSource;
  importance?: NoteImportance;
  tags?: string;
  reminder_at?: string | null;
  active_project_id?: number | null;
}


// ---------- AGENDA (rokovi + podsetnici) ----------

export type AgendaKind = "task" | "note" | "project";

export interface AgendaItem {
  kind: AgendaKind;
  ref_id: number;
  title: string;
  at: string;
  overdue: boolean;
  project_id: number | null;
  client_id: number | null;
  status: string;
  priority: string | null;
}

export interface AgendaResponse {
  count: number;
  days_ahead: number;
  include_overdue: boolean;
  items: AgendaItem[];
}


// ---------- PROJECT BRAIN (.codium/) ----------

export interface BrainFile {
  name: string;
  exists: boolean;
}

export interface BrainInfo {
  project_id: number;
  path: string;
  exists: boolean;
  files: BrainFile[];
}

export interface BrainFileContent {
  name: string;
  content: string;
}

export interface DevlogIndex {
  content: string;
}


// ---------- EXPLORER (file tree) ----------

export interface FileNode {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
}

export interface FileListResponse {
  path: string;
  count: number;
  nodes: FileNode[];
}

export interface FileContent {
  path: string;
  content: string;
  truncated: boolean;
  binary: boolean;
}


// ==========          VREMENSKA LINIJA AKTIVNOSTI          ==========

/** Jedan red u „Live Activity" — poziv modela ili odbijena akcija. */
export interface ActivityItem {
  at: string;
  /** "model" (poziv modela) ili "gate" (odbijena akcija). */
  kind: string;
  title: string;
  meta: string;
  /** "ok" | "error" | "blocked" */
  outcome: string;
  /** Odgovor ScopeGate-a; popunjeno samo za `gate`. */
  verdict: string;
  project_id: number | null;
  cost_usd: number;
}

export interface ActivityResponse {
  count: number;
  items: ActivityItem[];
}


// ==========          DOZVOLE, MOLBE I DNEVNIK          ==========

export type ScopeVerdict = "allow" | "deny" | "needs_approval";

export type ScopeRule = {
  id: number | null;
  actor: string;
  action: string;
  target: string;
  verdict: ScopeVerdict;
  note: string;
};

export type ScopeRulesResponse = { count: number; rules: ScopeRule[] };

export type ScopeRuleRequest = {
  actor: string;
  action: string;
  target: string;
  verdict: ScopeVerdict;
  note: string;
};

export type Approval = {
  id: number;
  actor: string;
  action: string;
  target: string;
  payload: string;
  status: string;
  note: string;
  requested_at: string;
  decided_at: string | null;
};

export type ApprovalsResponse = { count: number; approvals: Approval[] };

export type AuditEntry = {
  id: number | null;
  at: string;
  actor: string;
  action: string;
  target: string;
  verdict: string;
  outcome: string;
  detail: string;
  project_id: number | null;
};

export type AuditLogResponse = { count: number; entries: AuditEntry[] };


// ==========          AGENTI          ==========

export type AgentSummary = {
  id: number;
  slug: string;
  name: string;
  description: string;
  system_prompt: string;
  model: string;
  provider: string;
  tools: string[];
  max_steps: number;
  enabled: boolean;
};

export type AgentsResponse = { count: number; agents: AgentSummary[] };

export type AgentPatch = {
  name?: string;
  description?: string;
  system_prompt?: string;
  model?: string;
  provider?: string;
  tools?: string[];
  max_steps?: number;
  enabled?: boolean;
};

export type AgentTool = {
  name: string;
  description: string;
  action: string;
  args: Record<string, string>;
  writes_content: boolean;
};

export type AgentToolsResponse = { count: number; tools: AgentTool[] };

export type AgentStep = {
  idx: number;
  kind: string;
  tool: string;
  payload: string;
  at: string;
};

export type AgentRunSummary = {
  id: number;
  agent_id: number;
  agent_slug: string;
  project_id: number | null;
  task: string;
  status: string;
  result: string;
  steps_used: number;
  cost_usd: number;
  pending_approval_id: number | null;
  started_at: string;
  finished_at: string | null;
};

export type AgentRunsResponse = { count: number; runs: AgentRunSummary[] };

export type AgentRunResponse = { run: AgentRunSummary; steps: AgentStep[] };

export type AgentRunStarted = { run_id: number };

// ==========          REPOZITORIJUMI (E2)          ==========

export interface RepoStatus {
  branch: string;
  dirty: boolean;
  changed_files: number;
  ahead: number;
  behind: number;
  missing: boolean;
}

export interface Repository {
  id: number;
  project_id: number | null;
  name: string;
  local_path: string;
  remote_url: string | null;
  default_branch: string;
  provider: string;
  last_synced_at: string | null;
}

export interface RepositoryWithStatus extends Repository {
  status: RepoStatus;
}

export interface BranchInfo {
  name: string;
  is_current: boolean;
  target: string;
}

export interface CommitInfo {
  sha: string;
  short_sha: string;
  author: string;
  date: string;
  subject: string;
  body: string;
  files_changed: number;
  insertions: number;
  deletions: number;
}

export interface RepoSuggestion {
  project_id: number;
  project_name: string;
  local_path: string;
}

export interface RepositoriesResponse {
  repositories: RepositoryWithStatus[];
}

export interface BranchesResponse {
  branches: BranchInfo[];
}

export interface CommitsResponse {
  commits: CommitInfo[];
}

export interface DiffResponse {
  diff: string;
}

export interface FileAtResponse {
  content: string;
}

export interface SuggestionsResponse {
  suggestions: RepoSuggestion[];
}

export interface SyncResponse {
  executed: boolean;
  detail: string;
}

export interface RepositoryCreateRequest {
  local_path: string;
  project_id?: number | null;
  name?: string | null;
}

// ==========          PIPELINE-I (E3)          ==========

export interface Pipeline {
  id: number;
  repository_id: number;
  name: string;
  definition: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface PipelineRun {
  id: number;
  pipeline_id: number;
  status: string;
  trigger: string;
  commit_sha: string | null;
  branch: string | null;
  exit_code: number | null;
  detail: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface RunStep {
  idx: number;
  name: string;
  status: string;
  exit_code: number | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface RunLogLine {
  seq: number;
  step_idx: number;
  stream: string;
  line: string;
  at: string;
}

export interface PipelinesResponse {
  pipelines: Pipeline[];
}

export interface RunsResponse {
  runs: PipelineRun[];
}

export interface RunDetailResponse {
  run: PipelineRun;
  steps: RunStep[];
}

export interface RunLogsResponse {
  lines: RunLogLine[];
}

export interface CancelResponse {
  cancelled: boolean;
}

export interface PipelineCreateRequest {
  repository_id: number;
  definition: string;
}

export interface PipelineUpdateRequest {
  definition: string;
}


// ==========          ISPORUKA (E4)          ==========
// Deploy nema svoj build: ulaz je uspešno pokretanje iz E3 i paket koji je to
// pokretanje ostavilo.

/** Tip cilja isporuke. `ssh_host` postoji u backend-u, ali još nema provajdera. */
export type DeployKind = "local_folder" | "local_docker" | "ssh_host";

export type DeployStatus =
  | "pending"
  | "running"
  | "success"
  | "failed"
  | "rolled_back";

export interface DeployTarget {
  id: number;
  name: string;
  kind: DeployKind;
  /** Polja koja traži provajder (`path`, ili `mode`/`compose_dir`/`image`…). */
  config: Record<string, string>;
  project_id: number | null;
  connector_id: number | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface Deployment {
  id: number;
  target_id: number;
  run_id: number | null;
  commit_sha: string | null;
  status: DeployStatus;
  /** Čime se vraća unazad: folder prethodne verzije ili oznaka slike. */
  release_ref: string | null;
  detail: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface DeployHealth {
  healthy: boolean;
  detail: string;
}

export interface DeployTargetsResponse {
  targets: DeployTarget[];
}

export interface DeploymentsResponse {
  deployments: Deployment[];
}

export interface DeployableRunsResponse {
  run_ids: number[];
}

export interface DeployTargetCreateRequest {
  name: string;
  kind: DeployKind;
  config: Record<string, string>;
  project_id?: number | null;
}

export interface DeployTargetUpdateRequest {
  name: string;
  config: Record<string, string>;
  enabled: boolean;
}


// ==========          INFRASTRUKTURA (E5)          ==========
// Dva nivoa: `Node` je mesto gde nešto radi, `Service` je jedna stvar koja
// tamo radi.

export type NodeKind = "local" | "ssh";

export type InfraServiceKind = "local_process" | "local_docker" | "port_probe";

/** `unknown` = ne može da se utvrdi; `error` = pitali smo i dobili kvar. */
export type InfraServiceState = "running" | "stopped" | "unknown" | "error";

export interface InfraNode {
  id: number;
  name: string;
  kind: NodeKind;
  connector_id: number | null;
  created_at: string;
}

export interface InfraServiceStatus {
  state: InfraServiceState;
  pid: number | null;
  detail: string;
}

export interface InfraService {
  id: number;
  node_id: number;
  name: string;
  kind: InfraServiceKind;
  /** Polja koja traži provajder (`command`/`cwd`/`port`, `container`). */
  config: Record<string, string>;
  project_id: number | null;
  auto_start: boolean;
  created_at: string;
  updated_at: string;
  /** Živo stanje — ne čuva se u bazi, čita se od provajdera po zahtevu. */
  status: InfraServiceStatus;
}

/** Predlog, ne zapis: registar ostaje prazan dok čovek ne potvrdi. */
export interface DiscoveredService {
  name: string;
  kind: InfraServiceKind;
  config: Record<string, string>;
  state: InfraServiceState;
  detail: string;
  already_registered: boolean;
}

export interface InfraNodesResponse {
  nodes: InfraNode[];
}

export interface InfraServicesResponse {
  services: InfraService[];
}

export interface InfraDiscoverResponse {
  found: DiscoveredService[];
}

export interface InfraLogsResponse {
  lines: string[];
}

export interface InfraServiceCreateRequest {
  node_id: number;
  name: string;
  kind: InfraServiceKind;
  config: Record<string, string>;
  project_id?: number | null;
  auto_start?: boolean;
}


// ==========          MERENJE (E6)          ==========

export type AlertStateName = "firing" | "resolved";

export interface ServiceOverviewRow {
  service_id: number;
  name: string;
  kind: string;
  state: string;
  /** Poslednja izmerena vrednost `up` (1 = radi, 0 = ne odgovara). */
  up: number | null;
  latency_ms: number | null;
  cpu_percent: number | null;
  memory_mb: number | null;
  /** Udeo vremena u kojem je servis bio živ, u poslednja 24 sata (0..1). */
  uptime_24h: number | null;
  firing_alerts: number;
}

export interface MonitoringOverviewResponse {
  services: ServiceOverviewRow[];
}

export interface SeriesPoint {
  bucket: string;
  value: number;
  samples: number;
}

export interface MetricSeriesResponse {
  service_id: number;
  metric: string;
  bucket: string;
  points: SeriesPoint[];
}

export interface AlertRule {
  id: number;
  service_id: number | null;
  metric: string;
  comparison: string;
  threshold: number;
  for_samples: number;
  enabled: boolean;
  created_at: string;
}

export interface AlertRulesResponse {
  rules: AlertRule[];
}

export interface AlertRow {
  id: number;
  rule_id: number;
  state: AlertStateName | string;
  value: number | null;
  started_at: string;
  resolved_at: string | null;
}

export interface AlertsResponse {
  alerts: AlertRow[];
}

export interface AlertRuleCreateRequest {
  service_id: number;
  metric: string;
  comparison: string;
  threshold: number;
  for_samples?: number;
  enabled?: boolean;
}


// ==========          IZVEŠTAJI (E7)          ==========
// Svi izveštaji imaju ISTI oblik — zato GUI ima jednu komponentu grafikona,
// a ne osam.

export type ReportPeriod = "7d" | "30d" | "90d";

export type ReportSection = "razvoj" | "isporuka" | "sistem" | "ai";

export interface ReportPoint {
  /** Oznaka: dan (`2026-09-09`) ili ime (naziv koraka, modela, servisa). */
  x: string;
  y: number;
}

export interface ReportSeries {
  label: string;
  points: ReportPoint[];
}

export interface AnalyticsReport {
  name: string;
  period: string;
  series: ReportSeries[];
  /** Brojevi koje pločica prikazuje bez grafikona. */
  totals: Record<string, number>;
}

export interface ReportSpec {
  name: string;
  label: string;
  section: ReportSection | string;
  description: string;
  supports_project: boolean;
}

export interface ReportsListResponse {
  reports: ReportSpec[];
  periods: string[];
}

export interface AnalyticsSummaryResponse {
  period: string;
  totals: Record<string, number>;
}


// ==========          AUTOMATIZACIJA (E10)          ==========
// Pravilo ima tri dela: KADA (događaj), AKO (uslov), ONDA (akcije).

export type AutomationRunStatus =
  | "done"
  | "skipped"
  | "waiting_approval"
  | "failed"
  | "rate_limited";

export interface AutomationAction {
  name: string;
  params: Record<string, unknown>;
}

export interface AutomationRule {
  id: number;
  name: string;
  event: string;
  condition_expr: string;
  actions: AutomationAction[];
  project_id: number | null;
  enabled: boolean;
  rate_limit_n: number;
  rate_limit_seconds: number;
  created_at: string;
  updated_at: string;
  last_run_at: string | null;
}

export interface AutomationRulesResponse {
  rules: AutomationRule[];
}

export interface AutomationEventSpec {
  name: string;
  fields: string[];
}

export interface AutomationEventsResponse {
  events: AutomationEventSpec[];
}

export interface AutomationActionSpec {
  name: string;
  label: string;
  description: string;
  requires_approval: boolean;
  scope_action: string;
  params: string[];
}

export interface AutomationActionsResponse {
  actions: AutomationActionSpec[];
}

/** Ishod probe. Akcije NISU izvršene. */
export interface AutomationTestResponse {
  matched: boolean;
  reason: string;
  would_run: string[];
}

export interface AutomationRunRow {
  id: number;
  rule_id: number;
  event_json: string;
  matched: boolean;
  status: AutomationRunStatus | string;
  detail: string;
  at: string;
}

export interface AutomationRunsResponse {
  runs: AutomationRunRow[];
}

export interface AutomationRuleCreateRequest {
  name: string;
  event: string;
  condition_expr: string;
  actions: AutomationAction[];
  enabled?: boolean;
  rate_limit_n?: number;
  rate_limit_seconds?: number;
}

export interface AutomationRuleUpdateRequest {
  name: string;
  condition_expr: string;
  actions: AutomationAction[];
  enabled: boolean;
  rate_limit_n: number;
  rate_limit_seconds: number;
}
