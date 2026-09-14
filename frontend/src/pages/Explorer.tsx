/**
 * Repository Explorer page — file tree + code viewer.
 * Full implementation in Phase 8.
 */

import { useState, useEffect } from 'react';
import { FolderTree, FileCode, ChevronRight, ChevronDown } from 'lucide-react';
import { listRepositories, getFileTree, getFileContent } from '../services/api';
import type { Repository, FileInfo } from '../types';

function FileTreeNode({ file, depth = 0, onSelect }: {
  file: FileInfo;
  depth?: number;
  onSelect: (path: string) => void;
}) {
  const [expanded, setExpanded] = useState(depth < 1);

  if (file.is_directory) {
    return (
      <div>
        <div
          className="sidebar-link"
          style={{ paddingLeft: 8 + depth * 16, fontSize: 12 }}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <FolderTree size={14} style={{ color: 'var(--accent-blue)' }} />
          <span>{file.path.split('/').pop()}</span>
        </div>
        {expanded && file.children?.map((child) => (
          <FileTreeNode key={child.path} file={child} depth={depth + 1} onSelect={onSelect} />
        ))}
      </div>
    );
  }

  return (
    <div
      className="sidebar-link"
      style={{ paddingLeft: 8 + depth * 16, fontSize: 12 }}
      onClick={() => onSelect(file.path)}
    >
      <FileCode size={14} style={{ color: 'var(--text-tertiary)' }} />
      <span>{file.path.split('/').pop()}</span>
    </div>
  );
}

export default function Explorer() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>('');
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [fileContent, setFileContent] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listRepositories()
      .then(data => {
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
        .then(data => setFiles(data.files))
        .catch(() => setFiles([]))
        .finally(() => setLoading(false));
    }
  }, [selectedRepo]);

  async function handleFileSelect(path: string) {
    setSelectedFile(path);
    try {
      const data = await getFileContent(selectedRepo, path);
      setFileContent(data.content);
    } catch {
      setFileContent('// Unable to load file content');
    }
  }

  return (
    <>
      <div className="main-header">
        <span className="main-header-title">Repository Explorer</span>
        {repos.length > 0 && (
          <select
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
            style={{
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-primary)',
              padding: '4px 8px',
              fontSize: 12,
            }}
          >
            {repos.map(r => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        )}
      </div>
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* File Tree */}
        <div style={{
          width: 280,
          borderRight: '1px solid var(--border-default)',
          overflowY: 'auto',
          padding: '8px 0',
        }}>
          {loading ? (
            <div className="loading-container"><div className="spinner" /></div>
          ) : files.length === 0 ? (
            <div className="empty-state">
              <FolderTree className="empty-state-icon" />
              <div className="empty-state-title">No files</div>
              <div className="empty-state-description">
                Add and index a repository to browse files.
              </div>
            </div>
          ) : (
            files.map(f => (
              <FileTreeNode key={f.path} file={f} onSelect={handleFileSelect} />
            ))
          )}
        </div>

        {/* Code Viewer */}
        <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
          {selectedFile ? (
            <div>
              <div style={{
                fontSize: 12,
                color: 'var(--text-secondary)',
                marginBottom: 8,
                fontFamily: 'monospace',
              }}>
                {selectedFile}
              </div>
              <pre className="code-block" style={{ whiteSpace: 'pre-wrap' }}>
                {fileContent}
              </pre>
            </div>
          ) : (
            <div className="empty-state">
              <FileCode className="empty-state-icon" />
              <div className="empty-state-title">Select a file</div>
              <div className="empty-state-description">
                Choose a file from the tree to view its contents.
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
