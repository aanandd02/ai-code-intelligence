# System Architecture & Technical Specifications

**Project**: AI Code Intelligence & Review Agent  
**Version**: 1.0.0  
**Stack**: FastAPI, React 18, Vite, TypeScript, Tailwind, Ollama, Qdrant, Tree-sitter, SQLite

---

## 1. System Overview

The AI Code Intelligence & Review Agent is designed as a modular, local-first system consisting of three primary tiers:
1. **Frontend IDE Experience**: A React single-page application providing code exploration, conversational AI, code review dashboards, automated test triggers, and git workflows.
2. **Backend Engine**: A high-performance asynchronous FastAPI service managing AST parsing, vector embeddings, autonomous agent execution, and security controls.
3. **Local Storage & Inference Engines**: Ollama for local model inference, Qdrant for dense vector similarity search, and SQLite for relational state and chat histories.

---

## 2. Component Architecture

```mermaid
graph TD
    subgraph Client["Frontend Client (React + TS + Tailwind)"]
        ChatUI[AI Chat & Citations]
        ReviewUI[Review Dashboard]
        InvestigateUI[Investigation & Timeline]
        ExplorerUI[File Explorer & Monaco]
        GitUI[Git & Patch Management]
    end

    subgraph API["FastAPI Application Layer"]
        RepoRouter[Repository Endpoints]
        HealthRouter[Health & System Endpoints]
        AgentEngine[Autonomous Multi-Step Agent]
        ToolRegistry[Tool Registry]
        ContextBuilder[Context & Prompt Builder]
        ReviewService[Static & LLM Reviewer]
        PatchService[Patch & Backup Service]
        TestRunner[Subprocess Test Runner]
    end

    subgraph IndexingEngine["Ingestion & Parsing Pipeline"]
        FileDiscovery[File Discovery & Gitignore]
        LangDetector[Language Detector]
        TreeSitterParser[Tree-sitter AST Parser]
        Chunker[Semantic AST Chunker]
        Hasher[SHA-256 Content Hasher]
    end

    subgraph Storage["Persistent Local Storage"]
        SQLite[(SQLite Database)]
        Qdrant[(Qdrant Vector DB)]
        Backups[(Patch Backup Vault)]
    end

    subgraph Inference["Local Inference (Ollama)"]
        OllamaLLM[Code LLM: codellama:7b]
        OllamaEmbed[Embedding: nomic-embed-text]
    end

    Client --> API
    API --> IndexingEngine
    API --> Storage
    API --> Inference
    IndexingEngine --> Storage
    IndexingEngine --> Inference
    AgentEngine --> ToolRegistry
    AgentEngine --> ContextBuilder
    ContextBuilder --> Inference
```

---

## 3. Detailed Data Flows

### Ingestion & Indexing Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as FastAPI
    participant Disc as File Discovery
    participant AST as Tree-sitter Chunker
    participant DB as SQLite
    participant Embed as Ollama Embeddings
    participant Qdrant as Qdrant Vector DB

    User->>API: POST /api/repositories/{id}/index
    API->>Disc: Scan repository directory (.gitignore respected)
    Disc-->>API: Yield source file list
    loop Each File
        API->>DB: Check SHA-256 content hash
        alt Unchanged File
            API->>API: Skip (Incremental Dedup)
        else Changed or New File
            API->>AST: Parse AST with Tree-sitter
            AST-->>API: Semantic CodeChunks (function, class, method)
            API->>Embed: Batch embed chunk texts (768-dim)
            Embed-->>API: Vectors
            API->>Qdrant: Upsert vectors + chunk metadata
            API->>DB: Insert File and Chunk records
        end
    end
    API->>DB: Update total_files, total_chunks, indexed_at
    API-->>User: IndexingJobResponse (completed)
```

---

### Autonomous Agent Reasoning Loop

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Agent as CodeAgent
    participant LLM as Ollama LLM
    participant Tools as Tool Registry
    participant Repo as Local Filesystem

    User->>Agent: Request: "Investigate why token refresh fails"
    loop Up to Max Iterations
        Agent->>LLM: Send Conversation + Available Tools Description
        LLM-->>Agent: JSON: {"thought": "...", "tool": "semantic_search", "args": {"query": "refresh token"}}
        Agent->>Tools: Execute semantic_search("refresh token")
        Tools-->>Agent: Relevant code chunks from Qdrant
        Agent->>LLM: Tool Result Observation
        LLM-->>Agent: JSON: {"thought": "Inspect file", "tool": "read_file", "args": {"file_path": "auth.py"}}
        Agent->>Repo: Read lines 40-90 of auth.py
        Repo-->>Agent: Code snippet
        Agent->>LLM: Tool Result Observation
        LLM-->>Agent: JSON: {"final_answer": "...", "diagnosis": "...", "suggested_fix": "..."}
    end
    Agent-->>User: Structured AgentResult with step-by-step ToolTimeline
```

---

## 4. Database Schema (SQLite)

- **`repositories`**: Registered projects, path, default branch, language breakdown, file/chunk counts, indexing timestamps.
- **`files`**: Discovered source files, repo-relative path, language, byte size, SHA-256 content hash.
- **`chunks`**: AST semantic code chunks, symbol name, symbol type, start line, end line, content hash, code content.
- **`indexing_jobs`**: Job status, files processed, chunks embedded, skipped chunks, execution durations, errors.
- **`chat_sessions`**: Multi-turn conversation sessions tied to a specific repository.
- **`messages`**: Individual user/assistant messages with JSON serialized citations and tool calls.
- **`reviews`**: Code review results with structured severity findings.
- **`investigations`**: Multi-step issue investigations with root cause diagnoses and tool execution traces.
- **`generated_patches`**: Unified diff proposals, target files, and application statuses.
- **`test_runs`**: Executed test suite outputs, command lines, exit codes, and durations.

---

## 5. Extensibility & Future Integrations

- **Custom Local Models**: Seamlessly configurable in `.env` or UI settings (`deepseek-coder:6.7b`, `qwen2.5-coder:7b`, `llama3.1:8b`).
- **Additional Grammars**: Easily register new Tree-sitter grammar packages in `backend/app/indexing/chunker.py`.
- **Custom Agent Tools**: Add new `@tool_registry.register` decorators to extend the agent's toolbelt with linters, formatters, or profiling tools.
