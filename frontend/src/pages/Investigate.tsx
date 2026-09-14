/**
 * Issue Investigation page.
 */

import { useState, useEffect } from 'react';
import { Bug, FileCode, Target, Wrench } from 'lucide-react';
import { listRepositories, investigate } from '../services/api';
import type { Repository, InvestigationResponse } from '../types';
import ToolTimeline from '../components/ToolTimeline';

export default function Investigate() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState('');
  const [issue, setIssue] = useState('');
  const [result, setResult] = useState<InvestigationResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listRepositories().then(data => {
      setRepos(data.repositories);
      if (data.repositories.length > 0) setSelectedRepo(data.repositories[0].id);
    }).catch(() => {});
  }, []);

  async function handleInvestigate(e: React.FormEvent) {
    e.preventDefault();
    if (!issue.trim() || !selectedRepo) return;
    setLoading(true);
    try {
      const data = await investigate(selectedRepo, issue);
      setResult(data);
    } catch (err: any) {
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="main-header">
        <span className="main-header-title">Investigate Issue</span>
        {repos.length > 0 && (
          <select value={selectedRepo} onChange={(e) => setSelectedRepo(e.target.value)}
            style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)', padding: '4px 8px', fontSize: 12 }}
          >
            {repos.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        )}
      </div>
      <div className="main-body">
        <form onSubmit={handleInvestigate} style={{ marginBottom: 24 }}>
          <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
            Describe the issue you want to investigate
          </label>
          <textarea
            className="input textarea"
            placeholder='e.g. "Users are randomly getting logged out after 5 minutes"'
            value={issue}
            onChange={(e) => setIssue(e.target.value)}
            style={{ minHeight: 100 }}
          />
          <div style={{ marginTop: 12 }}>
            <button className="btn btn-primary" type="submit" disabled={loading || !issue.trim()}>
              <Bug size={14} />
              {loading ? 'Investigating...' : 'Investigate'}
            </button>
          </div>
        </form>

        {loading ? (
          <div className="loading-container">
            <div className="spinner" />
            <span style={{ color: 'var(--text-secondary)' }}>Investigating issue across the repository...</span>
          </div>
        ) : result ? (
          <div className="animate-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {result.diagnosis && (
              <div className="card">
                <div className="card-header">
                  <span className="card-title"><Target size={16} style={{ display: 'inline', marginRight: 6 }} />Diagnosis</span>
                  <span className="badge badge-info">{(result.diagnosis.confidence * 100).toFixed(0)}% confidence</span>
                </div>
                <div style={{ fontSize: 14, marginBottom: 12 }}>{result.diagnosis.probable_root_cause}</div>
                {result.diagnosis.supporting_evidence.length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>Supporting Evidence</div>
                    <ul style={{ fontSize: 13, paddingLeft: 20 }}>
                      {result.diagnosis.supporting_evidence.map((e, i) => <li key={i} style={{ marginBottom: 2 }}>{e}</li>)}
                    </ul>
                  </div>
                )}
                {result.diagnosis.relevant_files.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {result.diagnosis.relevant_files.map((f, i) => (
                      <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, background: 'rgba(88, 166, 255, 0.1)', padding: '2px 8px', borderRadius: 4, fontSize: 11, color: 'var(--accent-blue)', fontFamily: 'monospace' }}>
                        <FileCode size={11} />{f}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
            {result.suggested_fix && (
              <div className="card">
                <div className="card-header">
                  <span className="card-title"><Wrench size={16} style={{ display: 'inline', marginRight: 6 }} />Suggested Fix</span>
                </div>
                <div style={{ fontSize: 14 }}>{result.suggested_fix.description}</div>
                {result.suggested_fix.expected_impact && (
                  <div style={{ fontSize: 13, color: 'var(--accent-green)', marginTop: 8 }}>
                    Expected Impact: {result.suggested_fix.expected_impact}
                  </div>
                )}
              </div>
            )}
            {result.tool_calls && result.tool_calls.length > 0 && (
              <ToolTimeline toolCalls={result.tool_calls} />
            )}
          </div>
        ) : null}
      </div>
    </>
  );
}
