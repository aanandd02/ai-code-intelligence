/**
 * Code Review page — review code for bugs, security issues, etc.
 */

import { useState, useEffect } from 'react';
import { ShieldCheck, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { listRepositories, reviewCode } from '../services/api';
import type { Repository, ReviewFinding } from '../types';

const severityConfig: Record<string, { color: string; icon: typeof AlertTriangle; bg: string }> = {
  critical: { color: 'var(--accent-red)', icon: AlertCircle, bg: 'rgba(248, 81, 73, 0.1)' },
  high: { color: 'var(--accent-orange)', icon: AlertTriangle, bg: 'rgba(210, 153, 34, 0.1)' },
  medium: { color: 'var(--accent-orange)', icon: AlertTriangle, bg: 'rgba(210, 153, 34, 0.08)' },
  low: { color: 'var(--accent-blue)', icon: Info, bg: 'rgba(88, 166, 255, 0.1)' },
  info: { color: 'var(--text-secondary)', icon: Info, bg: 'rgba(139, 148, 158, 0.1)' },
};

export default function Review() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState('');
  const [filePath, setFilePath] = useState('');
  const [code, setCode] = useState('');
  const [reviewType, setReviewType] = useState('full');
  const [findings, setFindings] = useState<ReviewFinding[]>([]);
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listRepositories().then(data => {
      setRepos(data.repositories);
      if (data.repositories.length > 0) setSelectedRepo(data.repositories[0].id);
    }).catch(() => {});
  }, []);

  async function handleReview(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedRepo || (!filePath && !code)) return;
    setLoading(true);
    try {
      const data = await reviewCode(selectedRepo, {
        file_path: filePath || undefined,
        code: code || undefined,
        review_type: reviewType,
      });
      setFindings(data.findings);
      setSummary(data.summary || '');
    } catch (err: any) {
      setSummary(`Error: ${err.response?.data?.detail || err.message}`);
      setFindings([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="main-header">
        <span className="main-header-title">Code Review</span>
        {repos.length > 0 && (
          <select
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
            style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)', padding: '4px 8px', fontSize: 12 }}
          >
            {repos.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        )}
      </div>
      <div className="main-body">
        <form onSubmit={handleReview} style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>File path (optional)</label>
              <input className="input" placeholder="src/auth/service.py" value={filePath} onChange={(e) => setFilePath(e.target.value)} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Review type</label>
              <select className="input" value={reviewType} onChange={(e) => setReviewType(e.target.value)} style={{ width: 150 }}>
                <option value="full">Full Review</option>
                <option value="security">Security</option>
                <option value="performance">Performance</option>
                <option value="bugs">Bug Detection</option>
              </select>
            </div>
          </div>
          <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Or paste code directly</label>
          <textarea
            className="input textarea"
            placeholder="Paste code here for review..."
            value={code}
            onChange={(e) => setCode(e.target.value)}
            style={{ minHeight: 120, fontFamily: 'monospace', fontSize: 13 }}
          />
          <div style={{ marginTop: 12 }}>
            <button className="btn btn-primary" type="submit" disabled={loading || (!filePath && !code)}>
              <ShieldCheck size={14} />
              {loading ? 'Reviewing...' : 'Review Code'}
            </button>
          </div>
        </form>

        {/* Results */}
        {loading ? (
          <div className="loading-container"><div className="spinner" /><span style={{ color: 'var(--text-secondary)' }}>Analyzing code...</span></div>
        ) : findings.length > 0 ? (
          <div>
            {summary && <div className="card" style={{ marginBottom: 16, padding: 16, fontSize: 14 }}>{summary}</div>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {findings.map((f, i) => {
                const cfg = severityConfig[f.severity] || severityConfig.info;
                const Icon = cfg.icon;
                return (
                  <div key={i} className="card animate-in" style={{ padding: 14, background: cfg.bg, borderColor: cfg.color + '30' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <Icon size={16} style={{ color: cfg.color }} />
                      <span className={`badge badge-${f.severity === 'critical' || f.severity === 'high' ? 'error' : f.severity === 'medium' ? 'warning' : 'info'}`}>
                        {f.severity}
                      </span>
                      <span style={{ fontWeight: 600, fontSize: 14 }}>{f.title}</span>
                      {f.file && <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'monospace', marginLeft: 'auto' }}>{f.file}{f.line ? `:${f.line}` : ''}</span>}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-primary)', marginBottom: 6 }}>{f.description}</div>
                    {f.recommendation && (
                      <div style={{ fontSize: 12, color: 'var(--accent-green)', background: 'rgba(63, 185, 80, 0.08)', padding: '6px 10px', borderRadius: 4 }}>
                        💡 {f.recommendation}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}
      </div>
    </>
  );
}
