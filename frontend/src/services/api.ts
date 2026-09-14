/**
 * Axios API client for the AI Code Intelligence backend.
 */

import axios from 'axios';
import type {
  Repository,
  RepositoryCreate,
  HealthResponse,
  IndexingJob,
  SearchResponse,
  ChatResponse,
  ChatSessionInfo,
  ReviewResponse,
  InvestigationResponse,
  GitStatus,
  ModelsCatalog,
  FileInfo,
  FileContent,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000, // 5 min for heavy backend operations
});

// ── Health ──────────────────────────────────────────────────────────────

export const getHealth = () =>
  api.get<HealthResponse>('/health').then(r => r.data);

// ── Repositories ────────────────────────────────────────────────────────

export const createRepository = (data: RepositoryCreate) =>
  api.post<Repository>('/repositories', data).then(r => r.data);

export const listRepositories = () =>
  api.get<{ repositories: Repository[]; total: number }>('/repositories').then(r => r.data);

export const getRepository = (id: string) =>
  api.get<Repository>(`/repositories/${id}`).then(r => r.data);

export const deleteRepository = (id: string) =>
  api.delete(`/repositories/${id}`);

// ── Indexing ────────────────────────────────────────────────────────────

export const indexRepository = (repoId: string, force = false) =>
  api.post<IndexingJob>(`/repositories/${repoId}/index`, null, { params: { force } }).then(r => r.data);

export const getIndexingStatus = (repoId: string) =>
  api.get<IndexingJob>(`/repositories/${repoId}/indexing-status`).then(r => r.data);

// ── Files ───────────────────────────────────────────────────────────────

export const getFileTree = (repoId: string) =>
  api.get<FileInfo[]>(`/repositories/${repoId}/tree`).then(r => ({ files: r.data }));

export const getFileContent = (repoId: string, filePath: string) =>
  api.get<FileContent>(`/repositories/${repoId}/file`, {
    params: { path: filePath },
  }).then(r => r.data);

// ── Search ──────────────────────────────────────────────────────────────

export const semanticSearch = (repoId: string, query: string, topK = 10) =>
  api.post<SearchResponse>(`/repositories/${repoId}/semantic-search`, {
    query,
    top_k: topK,
  }).then(r => r.data);

// ── Chat ────────────────────────────────────────────────────────────────

export const chat = (repoId: string, message: string, sessionId?: string, model?: string, provider?: string) =>
  api.post<ChatResponse>(
    `/repositories/${repoId}/chat`,
    {
      message,
      session_id: sessionId,
      model,
      provider,
    },
    {
      timeout: 600000, // 10 minutes for heavy local AI inference without frontend abort
    }
  ).then(r => r.data);

export const listChatSessions = (repoId: string) =>
  api.get<ChatSessionInfo[]>(`/repositories/${repoId}/chat/sessions`).then(r => r.data);

export const getChatSessionMessages = (repoId: string, sessionId: string) =>
  api.get<any[]>(`/repositories/${repoId}/chat/sessions/${sessionId}/messages`).then(r => r.data);

export const deleteChatSession = (repoId: string, sessionId: string) =>
  api.delete(`/repositories/${repoId}/chat/sessions/${sessionId}`).then(r => r.data);

export const clearAllChatSessions = (repoId: string) =>
  api.delete(`/repositories/${repoId}/chat/sessions`).then(r => r.data);

// ── Code Review ─────────────────────────────────────────────────────────

export const reviewCode = (repoId: string, data: {
  file_path?: string;
  code?: string;
  diff?: string;
  review_type?: string;
}) =>
  api.post<ReviewResponse>(`/repositories/${repoId}/review`, data).then(r => r.data);

// ── Investigation ───────────────────────────────────────────────────────

export const investigate = (repoId: string, issue: string) =>
  api.post<InvestigationResponse>(`/repositories/${repoId}/investigate`, {
    issue,
  }).then(r => r.data);

// ── Test Generation ─────────────────────────────────────────────────────

export const generateTests = (repoId: string, filePath: string, functionName?: string) =>
  api.post(`/repositories/${repoId}/generate-tests`, {
    file_path: filePath,
    function_name: functionName,
  }).then(r => r.data);

export const runTests = (repoId: string, command?: string) =>
  api.post(`/repositories/${repoId}/run-tests`, { command }).then(r => r.data);

// ── Git ─────────────────────────────────────────────────────────────────

export const getGitStatus = (repoId: string) =>
  api.get<GitStatus>(`/repositories/${repoId}/git/status`).then(r => r.data);

export const getGitDiff = (repoId: string) =>
  api.get(`/repositories/${repoId}/git/diff`).then(r => r.data);

export const getGitLog = (repoId: string, limit = 20) =>
  api.get(`/repositories/${repoId}/git/log`, { params: { max_commits: limit } }).then(r => r.data);

// ── Patch ───────────────────────────────────────────────────────────────

export const previewPatch = (repoId: string, data: unknown) =>
  api.post(`/repositories/${repoId}/patch/preview`, data).then(r => r.data);

export const applyPatch = (repoId: string, patchId: string) =>
  api.post(`/repositories/${repoId}/patch/apply`, {
    patch_id: patchId,
    create_backup: true,
  }).then(r => r.data);

// ── Models ──────────────────────────────────────────────────────────────

export const listModels = () =>
  api.get<ModelsCatalog>('/models').then(r => r.data);

export default api;
