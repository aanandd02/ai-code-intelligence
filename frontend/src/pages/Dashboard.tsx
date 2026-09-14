/**
 * Dashboard page — shows system health, repo stats, and recent activity.
 */

import { useEffect, useState } from 'react';
import {
  Plus,
  FolderOpen,
  FileCode,
} from 'lucide-react';
import { getHealth, listRepositories, createRepository } from '../services/api';
import type { HealthResponse, Repository } from '../types';

export default function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddRepo, setShowAddRepo] = useState(false);
  const [repoPath, setRepoPath] = useState('');
  const [addError, setAddError] = useState('');
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [h, r] = await Promise.all([
        getHealth().catch(() => null),
        listRepositories().catch(() => ({ repositories: [], total: 0 })),
      ]);
      setHealth(h);
      setRepos(r.repositories);
    } finally {
      setLoading(false);
    }
  }

  async function handleAddRepo(e: React.FormEvent) {
    e.preventDefault();
    if (!repoPath.trim()) return;
    setAdding(true);
    setAddError('');
    try {
      await createRepository({ path: repoPath.trim() });
      setRepoPath('');
      setShowAddRepo(false);
      loadData();
    } catch (err: any) {
      setAddError(err.response?.data?.detail || 'Failed to add repository');
    } finally {
      setAdding(false);
    }
  }



  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
          Loading dashboard...
        </span>
      </div>
    );
  }

  return (
    <div className="animate-in">
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{
          fontSize: 24,
          fontWeight: 700,
          background: 'var(--gradient-primary)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          marginBottom: 4,
        }}>
          AI Code Intelligence
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Repository-aware AI assistant — 100% local, zero API cost
        </p>
      </div>

      {/* Service Status */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">System Status</span>
          {health && (
            <span className={`badge badge-${health.status === 'healthy' ? 'ok' : health.status === 'degraded' ? 'warning' : 'error'}`}>
              {health.status}
            </span>
          )}
        </div>
        {health ? (
          <div className="status-grid">
            {Object.entries(health.services).map(([name, svc]) => (
              <div key={name} className="status-card">
                <div className={`status-dot ${svc.status}`} />
                <div className="status-info">
                  <div className="status-name">{name}</div>
                  <div className="status-message">
                    {svc.message}
                    {svc.version && ` (v${svc.version})`}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: 'var(--accent-red)', fontSize: 13 }}>
            ⚠ Unable to connect to backend. Is the server running?
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{repos.length}</div>
          <div className="stat-label">Repositories</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {repos.reduce((sum, r) => sum + r.total_files, 0)}
          </div>
          <div className="stat-label">Files</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {repos.reduce((sum, r) => sum + r.total_chunks, 0)}
          </div>
          <div className="stat-label">Indexed Chunks</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">$0</div>
          <div className="stat-label">API Cost</div>
        </div>
      </div>

      {/* Repositories */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Repositories</span>
          <button className="btn btn-primary btn-sm" onClick={() => setShowAddRepo(true)}>
            <Plus size={14} /> Add Repository
          </button>
        </div>

        {/* Add Repository Modal */}
        {showAddRepo && (
          <div className="modal-overlay" onClick={() => setShowAddRepo(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-title">Add Repository</div>
              <form onSubmit={handleAddRepo}>
                <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                  Local repository path
                </label>
                <input
                  className="input"
                  type="text"
                  placeholder="/path/to/your/project"
                  value={repoPath}
                  onChange={(e) => setRepoPath(e.target.value)}
                  autoFocus
                />
                {addError && (
                  <div style={{ color: 'var(--accent-red)', fontSize: 12, marginTop: 8 }}>
                    {addError}
                  </div>
                )}
                <div className="modal-actions">
                  <button type="button" className="btn btn-secondary" onClick={() => setShowAddRepo(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary" disabled={adding || !repoPath.trim()}>
                    {adding ? 'Adding...' : 'Add Repository'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Repository List */}
        {repos.length === 0 ? (
          <div className="empty-state">
            <FolderOpen className="empty-state-icon" />
            <div className="empty-state-title">No repositories yet</div>
            <div className="empty-state-description">
              Add a local Git repository to get started with AI-powered code analysis.
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {repos.map((repo) => (
              <div
                key={repo.id}
                style={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  transition: 'border-color var(--transition-fast)',
                  cursor: 'pointer',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--accent-blue)')}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-default)')}
              >
                <FileCode size={20} style={{ color: 'var(--accent-blue)', flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{repo.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                    {repo.path}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-secondary)' }}>
                  <span>{repo.total_files} files</span>
                  <span>{repo.total_chunks} chunks</span>
                  {repo.indexed_at ? (
                    <span className="badge badge-ok">indexed</span>
                  ) : (
                    <span className="badge badge-warning">not indexed</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
