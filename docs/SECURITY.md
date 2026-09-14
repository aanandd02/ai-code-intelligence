# Security Model & Operational Safeguards

**Project**: AI Code Intelligence & Review Agent  
**Revision**: 1.0 (Local Security Architecture)

---

## 1. Threat Model & Design Principles

Because the assistant operates locally on the developer's computer, security focuses on:
1. **Preventing Local Path Traversal**: Ensuring an agent or malicious request cannot escape the repository root to read `/etc/passwd`, SSH keys, or personal documents.
2. **Preventing Command Injection**: Preventing arbitrary shell commands from being executed during test runs.
3. **Safe Code Modification & Backups**: Ensuring code patches cannot destroy user work without immediate fallback copies.
4. **Data Isolation**: Guaranteeing that confidential source code never leaves the user's computer.

---

## 2. Path Containment Safeguards

All file reads, writes, and patch operations enforce strict path containment via `app.core.security.validate_path_containment()`:

```python
def validate_path_containment(base_dir: Path, target_path: str | Path) -> Path:
    base_resolved = base_dir.resolve()
    target_resolved = (base_resolved / target_path).resolve()
    try:
        target_resolved.relative_to(base_resolved)
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: Path traversal attempt detected",
        )
    return target_resolved
```

### Verified Protections:
- `../../etc/passwd` ➔ **Blocked with HTTP 403 Forbidden**
- Symbolic link traversal outside the repo root ➔ **Blocked**
- Absolute path injections ➔ **Resolved and validated against repo root**

---

## 3. Subprocess Sandboxing & Command Allowlisting

When executing test suites, arbitrary shell commands (`rm -rf /`, `curl evil.com`, `sh -c`) are prohibited.
`app.services.test_runner` enforces:

1. **Strict Binary Allowlist**:
   - `pytest`
   - `python -m pytest`
   - `npm test`
   - `npm run test`
   - `npx vitest`
   - `npx jest`
   - `go test`
   - `cargo test`

2. **Metacharacter Stripping**:
   Commands containing semicolons (`;`), chaining operators (`&&`, `||`), pipes (`|`), subshells (`$()`, `` ` ``), or redirects (`>`, `<`) are rejected before subprocess invocation.

3. **Subprocess Execution without Shell**:
   Commands are passed as argument arrays (`argv`) directly to `asyncio.create_subprocess_exec` without `shell=True`.

4. **Hard Timeout Controls**:
   All test execution subprocesses are wrapped in a 60-second execution deadline to prevent runaway processes or fork bombs.

---

## 4. Atomic Patch Application with Automated Backups

Before any code modification or patch is written to disk:
1. A timestamped backup directory is created at `data/backups/<repo_id>/backup_<patch_id>_<timestamp>/`.
2. The exact pre-change file contents are archived.
3. If an error occurs midway, the operation aborts cleanly.
4. The backup directory reference is returned to the user for one-click audit or restoration.

---

## 5. Absolute Local Data Privacy

- **Local Inference**: All LLM completions execute on localhost (`http://localhost:11434`).
- **Local Vectors**: Embeddings and similarity search remain on localhost (`localhost:6333` or embedded SQLite/Qdrant storage).
- **Zero Cloud Egress**: Zero packets containing code or metadata are transmitted to external servers.
