import { useState, useEffect } from 'react';
import { Cpu, Cloud, WifiOff, Zap } from 'lucide-react';
import { listModels } from '../services/api';
import type { ModelsCatalog } from '../types';

interface ModelSelectorProps {
  selectedProvider: 'ollama' | 'groq';
  selectedModel: string;
  onSelect: (provider: 'ollama' | 'groq', model: string) => void;
}

export default function ModelSelector({
  selectedProvider,
  selectedModel,
  onSelect,
}: ModelSelectorProps) {
  const [catalog, setCatalog] = useState<ModelsCatalog | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listModels()
      .then(data => {
        setCatalog(data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const localProvider = catalog?.providers.find(p => p.id === 'ollama');
  const groqProvider = catalog?.providers.find(p => p.id === 'groq');

  const currentProviderInfo = selectedProvider === 'groq' ? groqProvider : localProvider;
  const availableModels = currentProviderInfo?.models || [];

  const handleProviderChange = (provider: 'ollama' | 'groq') => {
    const pInfo = provider === 'groq' ? groqProvider : localProvider;
    const defaultM = pInfo?.default_model || (pInfo?.models[0] ?? (provider === 'groq' ? 'openai/gpt-oss-120b' : 'qwen2.5-coder:7b'));
    onSelect(provider, defaultM);
  };

  const handleModelChange = (model: string) => {
    onSelect(selectedProvider, model);
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
      {/* Mode Switcher Pill */}
      <div
        style={{
          display: 'flex',
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-md)',
          padding: '2px',
          gap: 2,
        }}
      >
        <button
          type="button"
          onClick={() => handleProviderChange('ollama')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '4px 10px',
            fontSize: 12,
            fontWeight: 500,
            borderRadius: 'var(--radius-sm)',
            border: 'none',
            cursor: 'pointer',
            background: selectedProvider === 'ollama' ? 'var(--accent-blue)' : 'transparent',
            color: selectedProvider === 'ollama' ? '#fff' : 'var(--text-secondary)',
            transition: 'var(--transition-fast)',
          }}
          title="100% local, runs on your machine without internet ($0 cost)"
        >
          <Cpu size={13} />
          <span>Local (Offline)</span>
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: selectedProvider === 'ollama' ? '#fff' : 'var(--accent-green)',
            }}
          />
        </button>

        <button
          type="button"
          onClick={() => handleProviderChange('groq')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '4px 10px',
            fontSize: 12,
            fontWeight: 500,
            borderRadius: 'var(--radius-sm)',
            border: 'none',
            cursor: 'pointer',
            background: selectedProvider === 'groq' ? 'var(--accent-purple)' : 'transparent',
            color: selectedProvider === 'groq' ? '#fff' : 'var(--text-secondary)',
            transition: 'var(--transition-fast)',
          }}
          title="High-speed online inference via Groq cloud API"
        >
          <Cloud size={13} />
          <span>Cloud (Online)</span>
          <Zap size={11} style={{ opacity: 0.8 }} />
        </button>
      </div>

      {/* Model Dropdown for selected provider */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <select
          value={selectedModel}
          onChange={(e) => handleModelChange(e.target.value)}
          disabled={loading || availableModels.length === 0}
          style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-primary)',
            padding: '5px 10px',
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
            minWidth: 160,
          }}
        >
          {availableModels.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
          {availableModels.length === 0 && (
            <option value={selectedModel}>{selectedModel || 'Loading models...'}</option>
          )}
        </select>

        {/* Offline / Privacy Badge */}
        {selectedProvider === 'ollama' ? (
          <span
            className="badge badge-ok"
            style={{ fontSize: 10, display: 'inline-flex', alignItems: 'center', gap: 4 }}
            title="Runs locally without internet"
          >
            <WifiOff size={10} /> 100% Offline
          </span>
        ) : (
          <span
            className="badge"
            style={{
              fontSize: 10,
              background: 'rgba(188, 140, 255, 0.15)',
              color: 'var(--accent-purple)',
              borderColor: 'rgba(188, 140, 255, 0.3)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
            }}
            title="Cloud inference via Groq"
          >
            <Cloud size={10} /> Cloud Fast
          </span>
        )}
      </div>
    </div>
  );
}
