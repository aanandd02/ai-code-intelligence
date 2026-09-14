/**
 * Git integration page — branch, status, diff, log.
 */

import { useState, useEffect } from 'react';
import { GitBranch, GitCommit, FileDiff } from 'lucide-react';
import { listRepositories, getGitStatus, getGitDiff, getGitLog } from '../services/api';
import type { Repository, GitStatus, GitLogEntry } from '../types';

export default function Git() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState('');
  const [status, setStatus] = useState<GitStatus | null>(null);
  const [diff, setDiff] = useState('');
  const [log, setLog] = useState<GitLogEntry[]>([]);
  const [activeTab, setActiveTab] = useState<'status' | 'diff' | 'log'>('status');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listRepositories().then(data => {
      setRepos(data.repositories);
      if (data.repositories.length > 0) setSelectedRepo(data.repositories[0].id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedRepo) loadGitData();
  }, [selectedRepo]);

  async function loadGitData() {
    setLoading(true);
    try {
      const [s, d, l] = await Promise.all([
        getGitStatus(selectedRepo).catch(() => null),
        getGitDiff(selectedRepo).catch(() => ({ diff: '' })),
        getGitLog(selectedRepo, 20).catch(() => ({ entries: [] })),
      ]);
      setStatus(s);
      setDiff((d as any)?.diff || '');
      setLog((l as any)?.entries || []);
    } finally {
      setLoading(false);
    }
  }

  const tabs = [
    { key: 'status', label: 'Status' },
    { key: 'diff', label: 'Diff' },
    { key: 'log', label: 'History' },
  ] as const;

  return (
    <>
      <div className="main-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span className="main-header-title">Git</span>
          <div style={{ display: 'flex', gap: 2 }}>
            {tabs.map(t => (
              <button
                key={t.key}
                className={`btn btn-sm ${activeTab === t.key ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab(t.key)}
                style={{ borderRadius: 'var(--radius-sm)' }}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
        {repos.length > 0 && (
          <select value={selectedRepo} onChange={(e) => setSelectedRepo(e.target.value)}
            style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)', padding: '4px 8px', fontSize: 12 }}
          >
            {repos.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        )}
      </div>
      <div className="main-body">
        {loading ? (
          <div className="loading-container"><div className="spinner" /></div>
        ) : activeTab === 'status' && status ? (
          <div className="animate-in">
            <div className="card" style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <GitBranch size={16} style={{ color: 'var(--accent-purple)' }} />
                <span style={{ fontWeight: 600 }}>{status.branch || 'detached HEAD'}</span>
                <span className={`badge ${status.is_dirty ? 'badge-warning' : 'badge-ok'}`}>
                  {status.is_dirty ? 'dirty' : 'clean'}
                </span>
              </div>
              {status.commit_hash && (
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'monospace' }}>
                  {status.commit_hash?.slice(0, 8)} — {status.commit_message}
                </div>
              )}
            </div>
            {status.changed_files.length > 0 && (
              <div className="card">
                <div className="card-title" style={{ marginBottom: 8 }}>Changed Files ({status.changed_files.length})</div>
                {status.changed_files.map((f, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', fontSize: 13, fontFamily: 'monospace' }}>
                    <span className={`badge badge-${f.status === 'A' ? 'ok' : f.status === 'D' ? 'error' : 'warning'}`} style={{ fontSize: 10, minWidth: 16, textAlign: 'center' }}>
                      {f.status}
                    </span>
                    {f.path}
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : activeTab === 'diff' ? (
          <div className="animate-in">
            {diff ? (
              <pre className="code-block" style={{ fontSize: 12, whiteSpace: 'pre-wrap' }}>{diff}</pre>
            ) : (
              <div className="empty-state">
                <FileDiff className="empty-state-icon" />
                <div className="empty-state-title">No changes</div>
                <div className="empty-state-description">Working directory is clean.</div>
              </div>
            )}
          </div>
        ) : activeTab === 'log' ? (
          <div className="animate-in" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {log.map((entry, i) => (
              <div key={i} className="card" style={{ padding: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <GitCommit size={14} style={{ color: 'var(--accent-purple)' }} />
                  <span style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--accent-blue)' }}>{entry.short_hash}</span>
                  <span style={{ fontSize: 13, fontWeight: 500, flex: 1 }}>{entry.message}</span>
                  <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{new Date(entry.date).toLocaleDateString()}</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>
                  {entry.author} • {entry.files_changed} files changed
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </>
  );
}
