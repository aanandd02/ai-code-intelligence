/**
 * Test Generation & Execution page.
 */

import { useState, useEffect } from 'react';
import { TestTube, Play, CheckCircle, XCircle, Clock } from 'lucide-react';
import { listRepositories, generateTests, runTests } from '../services/api';


export default function Tests() {
  const [selectedRepo, setSelectedRepo] = useState('');
  const [filePath, setFilePath] = useState('');
  const [functionName, setFunctionName] = useState('');
  const [generatedCode, setGeneratedCode] = useState('');
  const [testCommand, setTestCommand] = useState('');
  const [testOutput, setTestOutput] = useState<{ stdout?: string; stderr?: string; exit_code?: number; status?: string; duration_seconds?: number } | null>(null);
  const [generating, setGenerating] = useState(false);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    listRepositories().then(data => {
      if (data.repositories.length > 0) setSelectedRepo(data.repositories[0].id);
    }).catch(() => {});
  }, []);

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!filePath || !selectedRepo) return;
    setGenerating(true);
    try {
      const data = await generateTests(selectedRepo, filePath, functionName || undefined);
      setGeneratedCode(data.test_code);
    } catch (err: any) {
      setGeneratedCode(`// Error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setGenerating(false);
    }
  }

  async function handleRunTests() {
    if (!selectedRepo) return;
    setRunning(true);
    setTestOutput(null);
    try {
      const data = await runTests(selectedRepo, testCommand || undefined);
      setTestOutput(data);
    } catch (err: any) {
      setTestOutput({ stderr: err.response?.data?.detail || err.message, exit_code: 1, status: 'error' });
    } finally {
      setRunning(false);
    }
  }

  return (
    <>
      <div className="main-header">
        <span className="main-header-title">Test Generation & Execution</span>
      </div>
      <div className="main-body">
        {/* Generate Tests */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-title" style={{ marginBottom: 12 }}>Generate Tests</div>
          <form onSubmit={handleGenerate}>
            <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
              <div style={{ flex: 2 }}>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>File path</label>
                <input className="input" placeholder="src/auth/service.py" value={filePath} onChange={(e) => setFilePath(e.target.value)} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>Function (optional)</label>
                <input className="input" placeholder="authenticate_user" value={functionName} onChange={(e) => setFunctionName(e.target.value)} />
              </div>
            </div>
            <button className="btn btn-primary" type="submit" disabled={generating || !filePath}>
              <TestTube size={14} />
              {generating ? 'Generating...' : 'Generate Tests'}
            </button>
          </form>
          {generatedCode && (
            <pre className="code-block" style={{ marginTop: 12, maxHeight: 400, overflow: 'auto', fontSize: 12 }}>
              {generatedCode}
            </pre>
          )}
        </div>

        {/* Run Tests */}
        <div className="card">
          <div className="card-title" style={{ marginBottom: 12 }}>Run Tests</div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <input className="input" placeholder="pytest (auto-detected if empty)" value={testCommand} onChange={(e) => setTestCommand(e.target.value)} style={{ flex: 1 }} />
            <button className="btn btn-primary" onClick={handleRunTests} disabled={running}>
              <Play size={14} />
              {running ? 'Running...' : 'Run Tests'}
            </button>
          </div>
          {testOutput && (
            <div className="animate-in">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                {testOutput.status === 'passed' ? (
                  <CheckCircle size={16} style={{ color: 'var(--accent-green)' }} />
                ) : (
                  <XCircle size={16} style={{ color: 'var(--accent-red)' }} />
                )}
                <span className={`badge ${testOutput.status === 'passed' ? 'badge-ok' : 'badge-error'}`}>
                  {testOutput.status} (exit {testOutput.exit_code})
                </span>
                {testOutput.duration_seconds && (
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Clock size={12} /> {testOutput.duration_seconds.toFixed(2)}s
                  </span>
                )}
              </div>
              {testOutput.stdout && <pre className="code-block" style={{ fontSize: 12, marginBottom: 8 }}>{testOutput.stdout}</pre>}
              {testOutput.stderr && <pre className="code-block" style={{ fontSize: 12, color: 'var(--accent-red)' }}>{testOutput.stderr}</pre>}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
