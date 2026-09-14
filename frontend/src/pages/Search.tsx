/**
 * Semantic Search page.
 */

import { useState, useEffect } from 'react';
import { Search as SearchIcon, FileCode, Zap } from 'lucide-react';
import { listRepositories, semanticSearch } from '../services/api';
import type { Repository, SearchResult } from '../types';

export default function SearchPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState('');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchedQuery, setSearchedQuery] = useState('');

  useEffect(() => {
    listRepositories().then(data => {
      setRepos(data.repositories);
      if (data.repositories.length > 0) setSelectedRepo(data.repositories[0].id);
    }).catch(() => {});
  }, []);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || !selectedRepo) return;
    setSearching(true);
    setSearchedQuery(query);
    try {
      const data = await semanticSearch(selectedRepo, query);
      setResults(data.results);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }

  return (
    <>
      <div className="main-header">
        <span className="main-header-title">Semantic Search</span>
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
            {repos.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        )}
      </div>
      <div className="main-body">
        {/* Search Form */}
        <form onSubmit={handleSearch} style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <SearchIcon
                size={16}
                style={{
                  position: 'absolute',
                  left: 12,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--text-tertiary)',
                }}
              />
              <input
                className="input"
                style={{ paddingLeft: 36 }}
                placeholder='Search code semantically, e.g. "Where is authentication handled?"'
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <button className="btn btn-primary" type="submit" disabled={searching || !query.trim()}>
              <Zap size={14} />
              {searching ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>

        {/* Results */}
        {searching ? (
          <div className="loading-container">
            <div className="spinner" />
            <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
              Searching repository...
            </span>
          </div>
        ) : results.length > 0 ? (
          <div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
              Found {results.length} results for "{searchedQuery}"
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {results.map((r, i) => (
                <div key={i} className="card" style={{ padding: 14 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <FileCode size={16} style={{ color: 'var(--accent-blue)' }} />
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{r.file_path}</span>
                    {r.symbol_name && (
                      <span style={{
                        background: 'rgba(188, 140, 255, 0.15)',
                        color: 'var(--accent-purple)',
                        padding: '1px 6px',
                        borderRadius: 4,
                        fontSize: 11,
                        fontWeight: 600,
                      }}>
                        {r.symbol_type}: {r.symbol_name}
                      </span>
                    )}
                    <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-tertiary)' }}>
                      Lines {r.start_line}–{r.end_line}
                    </span>
                    <span className="badge badge-info" style={{ marginLeft: 4 }}>
                      {(r.score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <pre className="code-block" style={{ fontSize: 12, maxHeight: 200, overflow: 'auto' }}>
                    {r.content}
                  </pre>
                </div>
              ))}
            </div>
          </div>
        ) : searchedQuery ? (
          <div className="empty-state">
            <SearchIcon className="empty-state-icon" />
            <div className="empty-state-title">No results</div>
            <div className="empty-state-description">
              No code matched your query. Try different wording or index the repository first.
            </div>
          </div>
        ) : (
          <div className="empty-state">
            <SearchIcon className="empty-state-icon" />
            <div className="empty-state-title">Semantic Code Search</div>
            <div className="empty-state-description">
              Search your codebase using natural language. The AI understands code semantics —
              try "Where is authentication handled?" or "Find database connection code".
            </div>
          </div>
        )}
      </div>
    </>
  );
}
