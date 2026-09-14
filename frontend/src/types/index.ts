/**
 * TypeScript type definitions for the AI Code Intelligence API.
 */

// ── Health ──────────────────────────────────────────────────────────────

export interface ServiceStatus {
  status: 'ok' | 'error' | 'unavailable';
  message?: string;
  version?: string;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  services: Record<string, ServiceStatus>;
  timestamp: string;
}

// ── Repository ──────────────────────────────────────────────────────────

export interface Repository {
  id: string;
  name: string;
  path: string;
  description?: string;
  default_branch?: string;
  languages?: string[];
  total_files: number;
  total_chunks: number;
  indexed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface RepositoryCreate {
  path: string;
  name?: string;
}

// ── File ────────────────────────────────────────────────────────────────

export interface FileInfo {
  path: string;
  language?: string;
  size_bytes: number;
  is_directory: boolean;
  children?: FileInfo[];
}

export interface FileContent {
  path: string;
  language?: string;
  content: string;
  size_bytes: number;
  line_count: number;
}

// ── Indexing ────────────────────────────────────────────────────────────

export interface IndexingJob {
  id: string;
  repository_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  total_files: number;
  processed_files: number;
  total_chunks: number;
  skipped_chunks: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
}

// ── Search ──────────────────────────────────────────────────────────────

export interface SearchResult {
  file_path: string;
  symbol_name?: string;
  symbol_type?: string;
  language?: string;
  start_line: number;
  end_line: number;
  content: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

// ── Chat ────────────────────────────────────────────────────────────────

export interface Citation {
  file_path: string;
  start_line?: number;
  end_line?: number;
  symbol_name?: string;
  content?: string;
}

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  tool_calls?: ToolCall[];
  model?: string;
  provider?: string;
  timestamp?: string;
}

export interface ChatResponse {
  session_id: string;
  message: string;
  citations: Citation[];
  model?: string;
  provider?: string;
  tool_calls?: ToolCall[];
}

// ── Tool Calls ──────────────────────────────────────────────────────────

export interface ToolCall {
  tool: string;
  arguments?: Record<string, unknown>;
  result?: string;
  status?: 'running' | 'completed' | 'error';
  duration_ms?: number;
}

// ── Review ──────────────────────────────────────────────────────────────

export interface ReviewFinding {
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  file?: string;
  line?: number;
  title: string;
  description: string;
  recommendation?: string;
  confidence: number;
}

export interface ReviewResponse {
  id: string;
  findings: ReviewFinding[];
  summary?: string;
  model?: string;
}

// ── Investigation ───────────────────────────────────────────────────────

export interface InvestigationDiagnosis {
  probable_root_cause: string;
  confidence: number;
  supporting_evidence: string[];
  affected_components: string[];
  relevant_files: string[];
  relevant_symbols: string[];
}

export interface SuggestedFix {
  description: string;
  affected_files: string[];
  expected_impact?: string;
  code_changes?: Record<string, unknown>[];
}

export interface InvestigationResponse {
  id: string;
  diagnosis?: InvestigationDiagnosis;
  suggested_fix?: SuggestedFix;
  validation?: Record<string, unknown>;
  tool_calls?: ToolCall[];
}

// ── Git ─────────────────────────────────────────────────────────────────

export interface GitStatus {
  branch?: string;
  is_dirty: boolean;
  changed_files: { path: string; status: string }[];
  untracked_files: string[];
  commit_hash?: string;
  commit_message?: string;
}

export interface GitLogEntry {
  hash: string;
  short_hash: string;
  author: string;
  date: string;
  message: string;
  files_changed: number;
}

// ── Models ──────────────────────────────────────────────────────────────

export interface OllamaModel {
  name: string;
  size?: string;
  modified_at?: string;
}

export interface LLMProviderInfo {
  id: 'ollama' | 'groq';
  name: string;
  description: string;
  is_available: boolean;
  models: string[];
  default_model: string;
}

export interface ModelsCatalog {
  providers: LLMProviderInfo[];
  active_provider: 'ollama' | 'groq';
  active_model: string;
  embedding_model?: string;
  models: { name: string }[];
  current_model: string;
}
