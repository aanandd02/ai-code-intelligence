/**
 * Settings page — model selection, configuration.
 */

import { useState, useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import { getHealth } from '../services/api';
import type { HealthResponse } from '../types';

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { refresh(); }, []);

  async function refresh() {
    setLoading(true);
    try {
      const h = await getHealth();
      setHealth(h);
    } catch { }
    finally { setLoading(false); }
  }

  return (
    <>
      <div className="main-header">
        <span className="main-header-title">Settings</span>
        <button className="btn btn-secondary btn-sm" onClick={refresh} disabled={loading}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>
      <div className="main-body">
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-title" style={{ marginBottom: 16 }}>System Configuration</div>
          <div className="status-grid">
            {health && Object.entries(health.services).map(([name, svc]) => (
              <div key={name} className="status-card">
                <div className={`status-dot ${svc.status}`} />
                <div className="status-info">
                  <div className="status-name">{name}</div>
                  <div className="status-message">{svc.message}{svc.version ? ` (v${svc.version})` : ''}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-title" style={{ marginBottom: 12 }}>Setup Instructions</div>
          <div style={{ fontSize: 13, lineHeight: 1.8 }}>
            <p style={{ marginBottom: 12 }}>
              This application runs <strong>100% locally</strong>. No API keys, no cloud costs.
            </p>
            <div className="code-block" style={{ fontSize: 12 }}>
              <div style={{ color: 'var(--text-secondary)', marginBottom: 8 }}># 1. Install Ollama (if not already)</div>
              <div>brew install ollama</div>
              <div style={{ color: 'var(--text-secondary)', marginTop: 12, marginBottom: 8 }}># 2. Start Ollama</div>
              <div>ollama serve</div>
              <div style={{ color: 'var(--text-secondary)', marginTop: 12, marginBottom: 8 }}># 3. Pull models</div>
              <div>ollama pull codellama:7b</div>
              <div>ollama pull nomic-embed-text</div>
              <div style={{ color: 'var(--text-secondary)', marginTop: 12, marginBottom: 8 }}># 4. Start the stack</div>
              <div>docker compose up -d</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-title" style={{ marginBottom: 8 }}>Cost Summary</div>
          <div style={{
            fontSize: 24,
            fontWeight: 700,
            background: 'var(--gradient-accent)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: 4,
          }}>
            TOTAL COST: $0
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            All components are open-source and run locally. No API keys or subscriptions required.
          </div>
        </div>
      </div>
    </>
  );
}
