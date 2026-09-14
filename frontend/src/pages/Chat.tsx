/**
 * AI Chat page — repository-aware conversation with citations.
 */

import { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, FileCode, Loader2 } from 'lucide-react';
import { listRepositories, chat } from '../services/api';
import type { Repository, ChatMessage, Citation } from '../types';
import ToolTimeline from '../components/ToolTimeline';
import ModelSelector from '../components/ModelSelector';
import MarkdownRenderer from '../components/MarkdownRenderer';

function CitationBadge({ citation }: { citation: Citation }) {
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      background: 'rgba(88, 166, 255, 0.1)',
      border: '1px solid rgba(88, 166, 255, 0.2)',
      borderRadius: 4,
      padding: '2px 8px',
      fontSize: 11,
      color: 'var(--accent-blue)',
      cursor: 'pointer',
      fontFamily: 'monospace',
    }}>
      <FileCode size={11} />
      {citation.file_path}
      {citation.start_line && `:${citation.start_line}`}
      {citation.end_line && `-${citation.end_line}`}
    </span>
  );
}

export default function Chat() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [provider, setProvider] = useState<'ollama' | 'groq'>(() => {
    const saved = localStorage.getItem('ai_provider');
    return saved === 'groq' ? 'groq' : 'ollama';
  });
  const [model, setModel] = useState<string>(() => {
    const saved = localStorage.getItem('ai_model');
    return saved || 'qwen2.5-coder:7b';
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRepositories().then(data => {
      setRepos(data.repositories);
      if (data.repositories.length > 0) setSelectedRepo(data.repositories[0].id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleModelSelect = (newProvider: 'ollama' | 'groq', newModel: string) => {
    setProvider(newProvider);
    setModel(newModel);
    localStorage.setItem('ai_provider', newProvider);
    localStorage.setItem('ai_model', newModel);
  };

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || !selectedRepo || loading) return;

    const userMsg: ChatMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await chat(selectedRepo, input, sessionId, model, provider);
      setSessionId(response.session_id);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.message,
        citations: response.citations,
        tool_calls: response.tool_calls?.map(tc => ({
          ...tc,
          tool: tc.tool || (tc as any).name || 'unknown',
        })),
        model: response.model,
        provider: response.provider || provider,
      }]);
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${err.response?.data?.detail || err.message || 'Failed to get response'}`,
      }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="main-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className="main-header-title">AI Chat</span>
          {repos.length > 0 && (
            <select
              value={selectedRepo}
              onChange={(e) => { setSelectedRepo(e.target.value); setMessages([]); setSessionId(undefined); }}
              style={{
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-primary)',
                padding: '4px 8px',
                fontSize: 12,
              }}
            >
              {repos.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          )}
        </div>

        <ModelSelector
          selectedProvider={provider}
          selectedModel={model}
          onSelect={handleModelSelect}
        />
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
        {messages.length === 0 ? (
          <div className="empty-state" style={{ marginTop: 60 }}>
            <Bot size={48} style={{ color: 'var(--accent-blue)', opacity: 0.5 }} />
            <div className="empty-state-title">Repository-Aware AI Chat</div>
            <div className="empty-state-description">
              Ask questions about your codebase. The AI will retrieve relevant code and cite specific files and line ranges.
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center', marginTop: 8 }}>
              {[
                'Explain the architecture of this project',
                'Where is authentication handled?',
                'Find potential bugs in the code',
                'How does the database connection work?',
              ].map((q) => (
                <button
                  key={q}
                  className="btn btn-secondary btn-sm"
                  onClick={() => setInput(q)}
                  style={{ fontSize: 12 }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              className="animate-in"
              style={{
                display: 'flex',
                gap: 12,
                marginBottom: 20,
                alignItems: 'flex-start',
              }}
            >
              <div style={{
                width: 32,
                height: 32,
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                background: msg.role === 'user' ? 'var(--bg-elevated)' : 'rgba(88, 166, 255, 0.1)',
              }}>
                {msg.role === 'user' ? <User size={16} /> : <Bot size={16} style={{ color: 'var(--accent-blue)' }} />}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>{msg.role === 'user' ? 'You' : 'AI Assistant'}</span>
                  {msg.role === 'assistant' && (
                    <>
                      {msg.provider === 'groq' ? (
                        <span
                          className="badge"
                          style={{
                            fontSize: 10,
                            background: 'rgba(188, 140, 255, 0.15)',
                            color: 'var(--accent-purple)',
                            borderColor: 'rgba(188, 140, 255, 0.3)',
                            padding: '1px 6px',
                          }}
                        >
                          ☁️ Groq Cloud
                        </span>
                      ) : (
                        <span
                          className="badge badge-ok"
                          style={{ fontSize: 10, padding: '1px 6px' }}
                        >
                          🖥️ Local Offline
                        </span>
                      )}
                      {msg.model && (
                        <span style={{ fontWeight: 400, color: 'var(--text-muted)', fontSize: 11 }}>
                          ({msg.model})
                        </span>
                      )}
                    </>
                  )}
                </div>
                {msg.role === 'assistant' ? (
                  <MarkdownRenderer content={msg.content} />
                ) : (
                  <div style={{
                    fontSize: 14,
                    lineHeight: 1.6,
                    color: 'var(--text-primary)',
                    whiteSpace: 'pre-wrap',
                  }}>
                    {msg.content}
                  </div>
                )}
                {msg.citations && msg.citations.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
                    {msg.citations.map((c, j) => (
                      <CitationBadge key={j} citation={c} />
                    ))}
                  </div>
                )}
                {msg.tool_calls && msg.tool_calls.length > 0 && (
                  <ToolTimeline toolCalls={msg.tool_calls} />
                )}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>
            <Loader2 size={16} className="animate-pulse" style={{ animation: 'spin 1s linear infinite' }} />
            Thinking...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '12px 20px',
        borderTop: '1px solid var(--border-default)',
        background: 'var(--bg-secondary)',
      }}>
        <form onSubmit={handleSend} style={{ display: 'flex', gap: 8 }}>
          <input
            className="input"
            placeholder="Ask about your code..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading || !selectedRepo}
          />
          <button
            className="btn btn-primary"
            type="submit"
            disabled={loading || !input.trim() || !selectedRepo}
          >
            <Send size={14} />
          </button>
        </form>
      </div>
    </>
  );
}
