/**
 * Repository Explorer page — VS Code Monaco editor with full syntax highlighting,
 * interactive file tree with search/filter, line counts, language badges, and copy tools.
 */

import { useState, useEffect, useMemo } from 'react';
import {
  FolderTree,
  Folder,
  FolderOpen,
  FileCode,
  FileText,
  ChevronRight,
  ChevronDown,
  Copy,
  Check,
  Search,
  MessageSquare,
  RefreshCw,
  FolderGit2,
} from 'lucide-react';
import Editor from '@monaco-editor/react';
import { useNavigate } from 'react-router-dom';
import { listRepositories, getFileTree, getFileContent } from '../services/api';
import type { Repository, FileInfo } from '../types';

function getMonacoLanguage(filePath: string): string {
  const ext = filePath.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'py':
      return 'python';
    case 'ts':
    case 'tsx':
      return 'typescript';
    case 'js':
    case 'jsx':
    case 'mjs':
    case 'cjs':
      return 'javascript';
    case 'json':
      return 'json';
    case 'html':
      return 'html';
    case 'css':
      return 'css';
    case 'md':
    case 'markdown':
      return 'markdown';
    case 'yaml':
    case 'yml':
      return 'yaml';
    case 'sql':
      return 'sql';
    case 'sh':
    case 'bash':
    case 'zsh':
      return 'shell';
    case 'dockerfile':
      return 'dockerfile';
    case 'ini':
      return 'ini';
    case 'rs':
      return 'rust';
    case 'go':
      return 'go';
    case 'java':
      return 'java';
    case 'c':
    case 'cpp':
    case 'h':
      return 'cpp';
    default:
      if (filePath.toLowerCase().includes('dockerfile')) return 'dockerfile';
      return 'plaintext';
  }
}

function getFileLanguageLabel(filePath: string): string {
  const ext = filePath.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'py':
      return 'Python';
    case 'ts':
      return 'TypeScript';
    case 'tsx':
      return 'TypeScript React';
    case 'js':
      return 'JavaScript';
    case 'jsx':
      return 'JavaScript React';
    case 'json':
      return 'JSON';
    case 'html':
      return 'HTML';
    case 'css':
      return 'CSS';
    case 'md':
      return 'Markdown';
    case 'yaml':
    case 'yml':
      return 'YAML';
    case 'sql':
      return 'SQL';
    case 'dockerfile':
      return 'Docker';
    default:
      if (filePath.toLowerCase().includes('dockerfile')) return 'Docker';
      return ext?.toUpperCase() || 'Text';
  }
}

function formatBytes(bytes?: number): string {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function FileTreeNode({
  file,
  depth = 0,
  selectedFile,
  onSelect,
  searchQuery,
}: {
  file: FileInfo;
  depth?: number;
  selectedFile: string;
  onSelect: (path: string) => void;
  searchQuery?: string;
}) {
  const isSearchActive = Boolean(searchQuery && searchQuery.trim().length > 0);
  const [expanded, setExpanded] = useState(depth < 1 || isSearchActive);

  useEffect(() => {
    if (isSearchActive) setExpanded(true);
  }, [isSearchActive]);

  const name = file.path.split('/').pop() || file.path;

  if (file.is_directory) {
    return (
      <div>
        <div
          className="sidebar-link"
          style={{
            paddingLeft: 8 + depth * 14,
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            cursor: 'pointer',
            paddingTop: 4,
            paddingBottom: 4,
          }}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? (
            <ChevronDown size={13} style={{ color: 'var(--text-tertiary)' }} />
          ) : (
            <ChevronRight size={13} style={{ color: 'var(--text-tertiary)' }} />
          )}
          {expanded ? (
            <FolderOpen size={14} style={{ color: 'var(--accent-blue)' }} />
          ) : (
            <Folder size={14} style={{ color: 'var(--accent-blue)' }} />
          )}
          <span style={{ fontWeight: 500 }}>{name}</span>
        </div>
        {expanded &&
          file.children?.map((child) => (
            <FileTreeNode
              key={child.path}
              file={child}
              depth={depth + 1}
              selectedFile={selectedFile}
              onSelect={onSelect}
              searchQuery={searchQuery}
            />
          ))}
      </div>
    );
  }

  const isSelected = selectedFile === file.path;

  return (
    <div
      className="sidebar-link"
      style={{
        paddingLeft: 22 + depth * 14,
        fontSize: 12,
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        cursor: 'pointer',
        paddingTop: 4,
        paddingBottom: 4,
        background: isSelected ? 'var(--bg-elevated)' : 'transparent',
        borderLeft: isSelected ? '2px solid var(--accent-blue)' : '2px solid transparent',
        color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
        fontWeight: isSelected ? 600 : 400,
      }}
      onClick={() => onSelect(file.path)}
    >
      {file.path.endsWith('.md') ? (
        <FileText size={13} style={{ color: 'var(--accent-cyan)' }} />
      ) : (
        <FileCode
          size={13}
          style={{
            color: isSelected ? 'var(--accent-blue)' : 'var(--text-tertiary)',
          }}
        />
      )}
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {name}
      </span>
    </div>
  );
}

function filterTree(nodes: FileInfo[], query: string): FileInfo[] {
  if (!query) return nodes;
  const q = query.toLowerCase();

  function prune(node: FileInfo): FileInfo | null {
    if (!node.is_directory) {
      return node.path.toLowerCase().includes(q) ? node : null;
    }
    const filteredChildren = (node.children || [])
      .map(prune)
      .filter((c): c is FileInfo => c !== null);
    if (filteredChildren.length > 0 || node.path.toLowerCase().includes(q)) {
      return {
        ...node,
        children: filteredChildren,
      };
    }
    return null;
  }

  return nodes.map(prune).filter((n): n is FileInfo => n !== null);
}

export default function Explorer() {
  const navigate = useNavigate();
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>('');
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [fileContent, setFileContent] = useState<string>('');
  const [fileSize, setFileSize] = useState<number | undefined>();
  const [loading, setLoading] = useState(false);
  const [contentLoading, setContentLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    listRepositories()
      .then((data) => {
        setRepos(data.repositories);
        if (data.repositories.length > 0) {
          setSelectedRepo(data.repositories[0].id);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedRepo) {
      setLoading(true);
      getFileTree(selectedRepo)
        .then((data) => {
          setFiles(data.files);
          // Auto select first file if none selected
          if (!selectedFile && data.files.length > 0) {
            findFirstFile(data.files);
          }
        })
        .catch(() => setFiles([]))
        .finally(() => setLoading(false));
    }
  }, [selectedRepo]);

  function findFirstFile(nodes: FileInfo[]) {
    for (const node of nodes) {
      if (!node.is_directory) {
        handleFileSelect(node.path);
        return;
      }
      if (node.children && node.children.length > 0) {
        findFirstFile(node.children);
        return;
      }
    }
  }

  async function handleFileSelect(path: string) {
    setSelectedFile(path);
    setContentLoading(true);
    try {
      const data = await getFileContent(selectedRepo, path);
      setFileContent(data.content);
      setFileSize(data.size_bytes);
    } catch {
      setFileContent('// Unable to load file content');
    } finally {
      setContentLoading(false);
    }
  }

  const handleCopy = () => {
    if (!fileContent) return;
    navigator.clipboard.writeText(fileContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleAskAI = () => {
    if (!selectedFile) return;
    navigate(`/chat?query=${encodeURIComponent(`Explain this file: ${selectedFile}`)}`);
  };

  const filteredFiles = useMemo(() => {
    return filterTree(files, searchQuery);
  }, [files, searchQuery]);

  const lineCount = useMemo(() => {
    if (!fileContent) return 0;
    return fileContent.split('\n').length;
  }, [fileContent]);

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
          padding: '10px 20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className="main-header-title" style={{ fontSize: 16 }}>Repository Explorer</span>

          {/* Codebase Indicator */}
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
            title="Active repository codebase"
          >
            <FolderGit2 size={13} style={{ color: 'var(--accent-blue)' }} />
            <span style={{ color: 'var(--text-tertiary)', fontSize: 11 }}>Codebase:</span>
            {repos.length > 1 ? (
              <select
                value={selectedRepo}
                onChange={(e) => setSelectedRepo(e.target.value)}
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

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => {
              if (selectedRepo) {
                setLoading(true);
                getFileTree(selectedRepo)
                  .then((data) => setFiles(data.files))
                  .finally(() => setLoading(false));
              }
            }}
            title="Refresh File Tree"
            style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* ── Main Explorer Body: File Tree + Monaco Editor ──────────── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* ── Left Pane: File Tree ─────────────────────────────────── */}
        <div
          style={{
            width: 290,
            background: 'var(--bg-secondary)',
            borderRight: '1px solid var(--border-default)',
            display: 'flex',
            flexDirection: 'column',
            flexShrink: 0,
          }}
        >
          {/* File Search Input */}
          <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--border-muted)' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-sm)',
                padding: '4px 10px',
              }}
            >
              <Search size={13} style={{ color: 'var(--text-tertiary)' }} />
              <input
                type="text"
                placeholder="Filter files..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-primary)',
                  fontSize: 12,
                  outline: 'none',
                  width: '100%',
                }}
              />
            </div>
          </div>

          {/* Tree View */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '8px 4px' }}>
            {loading ? (
              <div className="loading-container" style={{ padding: '40px 0' }}>
                <div className="spinner" />
              </div>
            ) : filteredFiles.length === 0 ? (
              <div className="empty-state" style={{ padding: '40px 16px', textAlign: 'center' }}>
                <FolderTree className="empty-state-icon" style={{ margin: '0 auto 8px', opacity: 0.4 }} />
                <div className="empty-state-title" style={{ fontSize: 13 }}>No files found</div>
                <div className="empty-state-description" style={{ fontSize: 11 }}>
                  {searchQuery ? 'Try another search query' : 'Index repository to view source files.'}
                </div>
              </div>
            ) : (
              filteredFiles.map((f) => (
                <FileTreeNode
                  key={f.path}
                  file={f}
                  selectedFile={selectedFile}
                  onSelect={handleFileSelect}
                  searchQuery={searchQuery}
                />
              ))
            )}
          </div>
        </div>

        {/* ── Right Pane: Code Viewer (Monaco Editor) ──────────────── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: '#1e1e1e' }}>
          {selectedFile ? (
            <>
              {/* File Info / Action Toolbar */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 16px',
                  background: 'var(--bg-secondary)',
                  borderBottom: '1px solid var(--border-default)',
                  fontSize: 12,
                }}
              >
                {/* File Path & Stats */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'monospace' }}>
                    <FileCode size={14} style={{ color: 'var(--accent-blue)' }} />
                    <span>{selectedFile}</span>
                  </div>
                  <span
                    className="badge"
                    style={{
                      fontSize: 10,
                      background: 'rgba(88, 166, 255, 0.12)',
                      color: 'var(--accent-blue)',
                      borderColor: 'rgba(88, 166, 255, 0.25)',
                    }}
                  >
                    {getFileLanguageLabel(selectedFile)}
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                    {lineCount} lines {fileSize ? `• ${formatBytes(fileSize)}` : ''}
                  </span>
                </div>

                {/* Actions: Copy & Ask AI */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="btn btn-secondary btn-sm"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11 }}
                    title="Copy file content to clipboard"
                  >
                    {copied ? <Check size={12} style={{ color: 'var(--accent-green)' }} /> : <Copy size={12} />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleAskAI}
                    className="btn btn-primary btn-sm"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11 }}
                    title="Ask AI questions about this specific file"
                  >
                    <MessageSquare size={12} />
                    <span>Ask AI</span>
                  </button>
                </div>
              </div>

              {/* VS Code Monaco Editor */}
              <div style={{ flex: 1, position: 'relative' }}>
                {contentLoading ? (
                  <div
                    style={{
                      position: 'absolute',
                      inset: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: 'rgba(30, 30, 30, 0.7)',
                      zIndex: 10,
                    }}
                  >
                    <div className="spinner" />
                  </div>
                ) : null}

                <Editor
                  height="100%"
                  language={getMonacoLanguage(selectedFile)}
                  value={fileContent}
                  theme="vs-dark"
                  options={{
                    readOnly: true,
                    minimap: { enabled: true },
                    fontSize: 13,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    fontFamily: "'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                    renderLineHighlight: 'all',
                    smoothScrolling: true,
                    padding: { top: 12, bottom: 12 },
                    wordWrap: 'off',
                    folding: true,
                    bracketPairColorization: { enabled: true },
                  }}
                />
              </div>
            </>
          ) : (
            <div className="empty-state" style={{ marginTop: 100, textAlign: 'center' }}>
              <FileCode className="empty-state-icon" size={48} style={{ color: 'var(--accent-blue)', opacity: 0.4, margin: '0 auto 16px' }} />
              <div className="empty-state-title" style={{ fontSize: 16 }}>Select a File to View Code</div>
              <div className="empty-state-description" style={{ fontSize: 13, maxWidth: 380, margin: '0 auto' }}>
                Browse the directory tree on the left to view files with full VS Code syntax highlighting and metrics.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
