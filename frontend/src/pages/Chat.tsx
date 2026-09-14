/**
 * VIP AI Chat page — repository-aware conversation with citations,
 * interactive Local/Cloud toggle, chat history session drawer, and rich markdown rendering.
 */

import { useState, useEffect, useRef } from 'react';
import {
  Send,
  Bot,
  User,
  FileCode,
  Loader2,
  History,
  Plus,
  Trash2,
  FolderGit2,
  Sparkles,
  MessageSquare,
  Copy,
  Check,
  RefreshCw,
} from 'lucide-react';
import {
  listRepositories,
  chat,
  listChatSessions,
  getChatSessionMessages,
  deleteChatSession,
} from '../services/api';
import type { Repository, ChatMessage, Citation, ChatSessionInfo } from '../types';
import ToolTimeline from '../components/ToolTimeline';
import ModelSelector from '../components/ModelSelector';
import MarkdownRenderer from '../components/MarkdownRenderer';

function CitationBadge({ citation }: { citation: Citation }) {
  return (
    <span
      style={{
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
      }}
      title={citation.content || citation.file_path}
    >
      <FileCode size={11} />
      {citation.file_path}
      {citation.start_line && `:${citation.start_line}`}
      {citation.end_line && `-${citation.end_line}`}
    </span>
  );
}

function formatRelativeTime(dateStr?: string) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString();
  } catch {
    return '';
  }
}

export default function Chat() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [sessions, setSessions] = useState<ChatSessionInfo[]>([]);
  const [showHistory, setShowHistory] = useState(true);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);

  const [provider, setProvider] = useState<'ollama' | 'groq'>(() => {
    const saved = localStorage.getItem('ai_provider');
    return saved === 'groq' ? 'groq' : 'ollama';
  });
  const [model, setModel] = useState<string>(() => {
    const saved = localStorage.getItem('ai_model');
    return saved || 'qwen2.5-coder:7b';
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<any>(null);

  // Load repositories on mount
  useEffect(() => {
    listRepositories()
      .then((data) => {
        setRepos(data.repositories);
        if (data.repositories.length > 0) {
          const firstId = data.repositories[0].id;
          setSelectedRepo(firstId);
          loadSessions(firstId);
        }
      })
      .catch(() => {});
  }, []);

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Timer while thinking
  useEffect(() => {
    if (loading) {
      setElapsedSec(0);
      timerRef.current = setInterval(() => {
        setElapsedSec((s) => s + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [loading]);

  const loadSessions = (repoId: string) => {
    if (!repoId) return;
    setLoadingSessions(true);
    listChatSessions(repoId)
      .then((data) => setSessions(data))
      .catch(() => {})
      .finally(() => setLoadingSessions(false));
  };

  const handleSelectSession = async (s: ChatSessionInfo) => {
    if (s.id === sessionId) return;
    try {
      setLoading(true);
      const data = await getChatSessionMessages(selectedRepo, s.id);
      const loadedMessages: ChatMessage[] = data.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        citations: m.citations,
        model: m.model,
        provider: m.provider || (m.model?.includes('gpt-oss') ? 'groq' : 'ollama'),
      }));
      setSessionId(s.id);
      setMessages(loadedMessages);
    } catch (err) {
      console.error('Failed to load session messages', err);
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    setSessionId(undefined);
    setMessages([]);
  };

  const handleDeleteSession = async (e: React.MouseEvent, sid: string) => {
    e.stopPropagation();
    try {
      await deleteChatSession(selectedRepo, sid);
      setSessions((prev) => prev.filter((s) => s.id !== sid));
      if (sessionId === sid) {
        handleNewChat();
      }
    } catch (err) {
      console.error('Failed to delete session', err);
    }
  };

  const handleModelSelect = (newProvider: 'ollama' | 'groq', newModel: string) => {
    setProvider(newProvider);
    setModel(newModel);
    localStorage.setItem('ai_provider', newProvider);
    localStorage.setItem('ai_model', newModel);
  };

  const handleCopyMessage = (content: string, index: number) => {
    navigator.clipboard.writeText(content);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || !selectedRepo || loading) return;

    const userMsg: ChatMessage = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await chat(selectedRepo, input, sessionId, model, provider);
      setSessionId(response.session_id);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.message,
          citations: response.citations,
          tool_calls: response.tool_calls?.map((tc) => ({
            ...tc,
            tool: tc.tool || (tc as any).name || 'unknown',
          })),
          model: response.model,
          provider: response.provider || provider,
        },
      ]);
      // Refresh session history list to show new or updated conversation
      loadSessions(selectedRepo);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${err.response?.data?.detail || err.message || 'Failed to get response'}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const selectedRepoObj = repos.find((r) => r.id === selectedRepo);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* ── Top Header ─────────────────────────────────────────────── */}
      <div
        className="main-header"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 12,
          flexWrap: 'wrap',
          padding: '10px 20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Toggle History Sidebar Button */}
          <button
            type="button"
            onClick={() => setShowHistory((prev) => !prev)}
            className="btn btn-secondary btn-sm"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              background: showHistory ? 'var(--bg-elevated)' : 'transparent',
              borderColor: showHistory ? 'var(--accent-blue)' : 'var(--border-default)',
            }}
            title={showHistory ? 'Hide Chat History' : 'Show Chat History'}
          >
            <History size={13} style={{ color: showHistory ? 'var(--accent-blue)' : 'var(--text-secondary)' }} />
            <span>History</span>
            {sessions.length > 0 && (
              <span
                style={{
                  fontSize: 10,
                  background: 'var(--bg-active)',
                  borderRadius: 10,
                  padding: '1px 5px',
                  color: 'var(--text-muted)',
                }}
              >
                {sessions.length}
              </span>
            )}
          </button>

          <span className="main-header-title" style={{ fontSize: 16 }}>AI Chat</span>

          {/* Active Codebase Badge / Selector */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-md)',
              padding: '3px 10px',
              fontSize: 12,
            }}
            title="Active repository codebase being analyzed and referenced by the AI"
          >
            <FolderGit2 size={13} style={{ color: 'var(--accent-blue)' }} />
            <span style={{ color: 'var(--text-tertiary)', fontSize: 11, fontWeight: 500 }}>Codebase:</span>
            {repos.length > 1 ? (
              <select
                value={selectedRepo}
                onChange={(e) => {
                  setSelectedRepo(e.target.value);
                  handleNewChat();
                  loadSessions(e.target.value);
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-primary)',
                  fontWeight: 600,
                  cursor: 'pointer',
                  outline: 'none',
                  fontSize: 12,
                }}
              >
                {repos.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            ) : (
              <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 12 }}>
                {selectedRepoObj?.name || 'ai-code-intelligence'}
              </span>
            )}
          </div>
        </div>

        {/* Local vs Cloud Selector */}
        <ModelSelector
          selectedProvider={provider}
          selectedModel={model}
          onSelect={handleModelSelect}
        />
      </div>

      {/* ── Main Content Area: Sidebar + Messages ──────────────────── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* ── Chat History Sidebar ─────────────────────────────────── */}
        {showHistory && (
          <div
            style={{
              width: 260,
              background: 'var(--bg-secondary)',
              borderRight: '1px solid var(--border-default)',
              display: 'flex',
              flexDirection: 'column',
              flexShrink: 0,
            }}
          >
            {/* New Chat Button */}
            <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--border-muted)' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleNewChat}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  padding: '7px 12px',
                }}
              >
                <Plus size={14} />
                <span>New Chat</span>
              </button>
            </div>

            {/* Sessions List */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '10px 8px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '4px 8px',
                  marginBottom: 6,
                  color: 'var(--text-tertiary)',
                  fontSize: 11,
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                <span>Recent Conversations</span>
                <button
                  type="button"
                  onClick={() => loadSessions(selectedRepo)}
                  style={{ background: 'none', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer' }}
                  title="Refresh conversation list"
                >
                  <RefreshCw size={11} className={loadingSessions ? 'animate-spin' : ''} />
                </button>
              </div>

              {sessions.length === 0 ? (
                <div style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 12 }}>
                  <MessageSquare size={24} style={{ margin: '0 auto 8px', opacity: 0.3 }} />
                  <div>No past conversations</div>
                  <div style={{ fontSize: 11, marginTop: 4 }}>New chats will be saved here automatically.</div>
                </div>
              ) : (
                sessions.map((s) => {
                  const isActive = s.id === sessionId;
                  return (
                    <div
                      key={s.id}
                      onClick={() => handleSelectSession(s)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 10px',
                        marginBottom: 4,
                        borderRadius: 'var(--radius-sm)',
                        cursor: 'pointer',
                        background: isActive ? 'var(--bg-elevated)' : 'transparent',
                        border: isActive ? '1px solid var(--border-active)' : '1px solid transparent',
                        transition: 'var(--transition-fast)',
                      }}
                      className="sidebar-link"
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, flex: 1 }}>
                        <MessageSquare
                          size={13}
                          style={{
                            color: isActive ? 'var(--accent-blue)' : 'var(--text-secondary)',
                            flexShrink: 0,
                          }}
                        />
                        <div style={{ minWidth: 0, flex: 1 }}>
                          <div
                            style={{
                              fontSize: 12,
                              fontWeight: isActive ? 600 : 400,
                              color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}
                          >
                            {s.title || 'Untitled Conversation'}
                          </div>
                          {s.updated_at && (
                            <div style={{ fontSize: 10, color: 'var(--text-tertiary)', marginTop: 2 }}>
                              {formatRelativeTime(s.updated_at)}
                            </div>
                          )}
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={(e) => handleDeleteSession(e, s.id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--text-tertiary)',
                          padding: '3px 4px',
                          cursor: 'pointer',
                          borderRadius: 4,
                          display: 'inline-flex',
                          alignItems: 'center',
                          opacity: 0.6,
                        }}
                        title="Delete chat session"
                        onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--accent-red)')}
                        onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-tertiary)')}
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* ── Active Conversation Stream ───────────────────────────── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Message List */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
            {messages.length === 0 ? (
              <div className="empty-state" style={{ marginTop: 40, maxWidth: 640, marginLeft: 'auto', marginRight: 'auto' }}>
                <div
                  style={{
                    width: 56,
                    height: 56,
                    borderRadius: 'var(--radius-lg)',
                    background: 'rgba(88, 166, 255, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 16px',
                    color: 'var(--accent-blue)',
                  }}
                >
                  <Sparkles size={28} />
                </div>
                <div className="empty-state-title" style={{ fontSize: 18 }}>Repository-Aware AI Assistant</div>
                <div className="empty-state-description" style={{ fontSize: 13, lineHeight: 1.6 }}>
                  Direct semantic visibility into <strong>{selectedRepoObj?.name || 'ai-code-intelligence'}</strong>.
                  Ask questions, find bugs, or explore project architecture with concrete citations.
                </div>

                {/* VIP Suggested Prompts */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 10, marginTop: 20, textAlign: 'left' }}>
                  {[
                    { title: 'Explain the architecture of this project', desc: 'Overview of backend, frontend & data flow' },
                    { title: 'Find potential bugs in the code', desc: 'Scan files for unhandled errors & bugs' },
                    { title: 'Where is authentication handled?', desc: 'Security utilities & token management' },
                    { title: 'How does the database connection work?', desc: 'Async SQLAlchemy & SQLite setup' },
                  ].map((item) => (
                    <button
                      key={item.title}
                      className="card card-hover"
                      onClick={() => setInput(item.title)}
                      style={{
                        padding: '12px 14px',
                        cursor: 'pointer',
                        textAlign: 'left',
                        background: 'var(--bg-secondary)',
                        border: '1px solid var(--border-default)',
                        borderRadius: 'var(--radius-md)',
                      }}
                    >
                      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 3 }}>
                        {item.title}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                        {item.desc}
                      </div>
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
                    gap: 14,
                    marginBottom: 24,
                    alignItems: 'flex-start',
                  }}
                >
                  {/* Avatar */}
                  <div
                    style={{
                      width: 34,
                      height: 34,
                      borderRadius: 'var(--radius-md)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      background: msg.role === 'user' ? 'var(--bg-elevated)' : 'rgba(88, 166, 255, 0.12)',
                      border: msg.role === 'user' ? '1px solid var(--border-default)' : '1px solid rgba(88, 166, 255, 0.25)',
                    }}
                  >
                    {msg.role === 'user' ? <User size={16} /> : <Bot size={17} style={{ color: 'var(--accent-blue)' }} />}
                  </div>

                  {/* Message Bubble & Content */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    {/* Header */}
                    <div
                      style={{
                        fontSize: 12,
                        fontWeight: 600,
                        color: 'var(--text-secondary)',
                        marginBottom: 6,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                        <span style={{ color: msg.role === 'user' ? 'var(--text-primary)' : 'var(--text-link)' }}>
                          {msg.role === 'user' ? 'You' : 'AI Assistant'}
                        </span>
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

                      {/* Copy Button on Assistant Message */}
                      {msg.role === 'assistant' && (
                        <button
                          type="button"
                          onClick={() => handleCopyMessage(msg.content, i)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 4,
                            background: 'transparent',
                            border: 'none',
                            color: copiedIndex === i ? 'var(--accent-green)' : 'var(--text-tertiary)',
                            cursor: 'pointer',
                            fontSize: 11,
                            padding: '2px 6px',
                            borderRadius: 4,
                          }}
                          title="Copy entire answer"
                        >
                          {copiedIndex === i ? <Check size={12} /> : <Copy size={12} />}
                          <span>{copiedIndex === i ? 'Copied' : 'Copy'}</span>
                        </button>
                      )}
                    </div>

                    {/* Content */}
                    {msg.role === 'assistant' ? (
                      <MarkdownRenderer content={msg.content} />
                    ) : (
                      <div
                        style={{
                          fontSize: 14,
                          lineHeight: 1.6,
                          color: 'var(--text-primary)',
                          background: 'var(--bg-secondary)',
                          border: '1px solid var(--border-default)',
                          borderRadius: 'var(--radius-md)',
                          padding: '10px 14px',
                          display: 'inline-block',
                          maxWidth: '90%',
                          whiteSpace: 'pre-wrap',
                        }}
                      >
                        {msg.content}
                      </div>
                    )}

                    {/* Citations */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
                        {msg.citations.map((c, j) => (
                          <CitationBadge key={j} citation={c} />
                        ))}
                      </div>
                    )}

                    {/* Tool Calls */}
                    {msg.tool_calls && msg.tool_calls.length > 0 && (
                      <ToolTimeline toolCalls={msg.tool_calls} />
                    )}
                  </div>
                </div>
              ))
            )}

            {/* VIP Thinking State */}
            {loading && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '12px 16px',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: 16,
                  maxWidth: 580,
                }}
              >
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    background: provider === 'groq' ? 'rgba(188, 140, 255, 0.15)' : 'rgba(88, 166, 255, 0.15)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: provider === 'groq' ? 'var(--accent-purple)' : 'var(--accent-blue)',
                    flexShrink: 0,
                  }}
                >
                  <Loader2 size={16} style={{ animation: 'spin 1.2s linear infinite' }} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                    {provider === 'groq' ? (
                      <span>Groq Cloud ({model}) is generating response...</span>
                    ) : (
                      <span>Local AI ({model}) is analyzing codebase...</span>
                    )}
                    <span style={{ marginLeft: 8, color: 'var(--text-secondary)', fontWeight: 400, fontSize: 12 }}>
                      {elapsedSec}s
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>
                    Searching vector embeddings, AST symbols & analyzing repository architecture
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* ── Input Box at bottom ─────────────────────────────────── */}
          <div
            style={{
              padding: '14px 20px',
              borderTop: '1px solid var(--border-default)',
              background: 'var(--bg-secondary)',
            }}
          >
            <form onSubmit={handleSend} style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <input
                className="input"
                placeholder={`Ask anything about ${selectedRepoObj?.name || 'this repository'}...`}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading || !selectedRepo}
                style={{
                  height: 42,
                  fontSize: 13,
                  background: 'var(--bg-primary)',
                  borderRadius: 'var(--radius-md)',
                }}
              />
              <button
                className="btn btn-primary"
                type="submit"
                disabled={loading || !input.trim() || !selectedRepo}
                style={{
                  height: 42,
                  padding: '0 18px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  fontWeight: 600,
                  fontSize: 13,
                }}
              >
                <span>Send</span>
                <Send size={14} />
              </button>
            </form>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginTop: 6,
                fontSize: 11,
                color: 'var(--text-tertiary)',
                padding: '0 2px',
              }}
            >
              <span>Press <strong>Enter</strong> to send. All queries reference local files with line citations.</span>
              <span>
                {provider === 'groq' ? 'Cloud inference via Groq API' : '100% Offline • Zero cloud cost'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
