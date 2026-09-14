"""
Chat service managing conversational sessions, context augmentation,
Ollama LLM interactions, and persistent history with citations.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.context_builder import ContextBuilder
from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import ChatSession, Message, Repository
from app.llm.provider import get_llm_provider
from app.retrieval.search import semantic_search
from app.schemas.schemas import ChatResponse, Citation, SearchResult

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatService:
    """Orchestrates repository chat with semantic retrieval and conversation memory."""

    def __init__(self):
        self.context_builder = ContextBuilder()

    async def send_message(
        self,
        repo_id: str,
        user_content: str,
        session_id: str | None,
        model: str | None,
        session: AsyncSession,
        provider: str | None = None,
    ) -> ChatResponse:
        # 1. Fetch Repository
        res = await session.execute(select(Repository).where(Repository.id == repo_id))
        repo = res.scalar_one_or_none()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        # 2. Get or create ChatSession
        chat_sess = None
        if session_id:
            s_res = await session.execute(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.repository_id == repo_id,
                )
            )
            chat_sess = s_res.scalar_one_or_none()

        if not chat_sess:
            chat_sess = ChatSession(
                id=uuid.uuid4().hex,
                repository_id=repo_id,
                title=user_content[:50],
            )
            session.add(chat_sess)
            await session.commit()
            await session.refresh(chat_sess)

        # 3. Save User Message
        user_msg = Message(
            session_id=chat_sess.id,
            role="user",
            content=user_content,
        )
        session.add(user_msg)
        await session.commit()

        # 4. Context Augmentation via Semantic Search
        repo_languages = repo.languages_list if hasattr(repo, "languages_list") else []
        search_results = await semantic_search(
            query=user_content,
            repo_id=repo_id,
            top_k=settings.SEARCH_TOP_K,
        )

        snippets = list(search_results.results) if hasattr(search_results, "results") else []

        # If snippets are few (< 3) or query asks broad questions (e.g. bugs, architecture, overview),
        # supplement with key source files directly from the repository so the AI has concrete code to analyze.
        broad_keywords = {"bug", "bugs", "issue", "issues", "error", "architecture", "overview", "explain", "security", "structure", "audit", "review", "flow", "auth"}
        user_words = {w.strip("?,.!;:").lower() for w in user_content.split()}
        is_broad = bool(user_words & broad_keywords) or len(snippets) < 2

        if is_broad:
            repo_path_obj = Path(repo.path)
            candidate_files = [
                "backend/app/main.py",
                "backend/app/api/repositories.py",
                "backend/app/services/chat.py",
                "backend/app/core/config.py",
                "frontend/src/App.tsx",
                "frontend/src/pages/Chat.tsx",
            ]
            existing_paths = {s.file_path for s in snippets}
            for rel_f in candidate_files:
                target = repo_path_obj / rel_f
                if target.is_file() and rel_f not in existing_paths:
                    try:
                        lines = target.read_text(encoding="utf-8", errors="ignore").splitlines()
                        sample_lines = lines[:75]
                        snippets.append(
                            SearchResult(
                                file_path=rel_f,
                                symbol_name=None,
                                symbol_type="module_overview",
                                language="python" if rel_f.endswith(".py") else "typescript",
                                start_line=1,
                                end_line=len(sample_lines),
                                content="\n".join(sample_lines),
                                score=0.85,
                            )
                        )
                        if len(snippets) >= 5:
                            break
                    except Exception:
                        pass

        snippets_text, citations = self.context_builder.format_code_snippets(snippets)
        augmented_prompt = self.context_builder.assemble_user_prompt(user_content, snippets_text)

        # 5. Fetch recent chat history
        history_res = await session.execute(
            select(Message)
            .where(Message.session_id == chat_sess.id)
            .order_by(Message.created_at.asc())
        )
        all_msgs = history_res.scalars().all()

        chat_history: list[dict[str, str]] = []
        for m in all_msgs[:-1]:  # Exclude current user message which we will append augmented
            chat_history.append({"role": m.role, "content": m.content})

        chat_history.append({"role": "user", "content": augmented_prompt})

        # 6. Build system prompt
        system_prompt = self.context_builder.build_system_prompt(
            repo_name=repo.name,
            repo_path=Path(repo.path),
            languages=repo_languages,
        )

        # 7. Call LLM with user-selected or default provider
        from app.llm.provider import get_llm_for_model

        llm, target_model, active_provider = get_llm_for_model(model=model, provider=provider)
        assistant_reply = await llm.chat(
            messages=chat_history,
            system=system_prompt,
            model=target_model,
        )

        # 8. Save Assistant Message with Citations
        citations_data = [c.model_dump() for c in citations]
        assistant_msg = Message(
            session_id=chat_sess.id,
            role="assistant",
            content=assistant_reply,
            citations_json=json.dumps(citations_data),
            model=target_model,
        )
        session.add(assistant_msg)
        await session.commit()

        return ChatResponse(
            session_id=chat_sess.id,
            message=assistant_reply,
            citations=citations,
            model=target_model,
            provider=active_provider,
        )

    async def list_sessions(self, repo_id: str, session: AsyncSession) -> list[dict[str, Any]]:
        res = await session.execute(
            select(ChatSession)
            .where(ChatSession.repository_id == repo_id)
            .order_by(ChatSession.updated_at.desc())
        )
        sessions = res.scalars().all()
        return [
            {
                "id": s.id,
                "title": s.title or "Untitled Conversation",
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ]

    async def get_messages(self, session_id: str, session: AsyncSession) -> list[dict[str, Any]]:
        res = await session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        )
        messages = res.scalars().all()
        result = []
        for m in messages:
            citations = []
            if m.citations_json:
                try:
                    citations = json.loads(m.citations_json)
                except Exception:
                    citations = []

            provider_id = "groq" if (m.model and ("gpt-oss" in m.model or "qwen3.8" in m.model)) else "ollama"
            result.append({
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "citations": citations,
                "model": m.model,
                "provider": provider_id,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            })
        return result

    async def delete_session(self, session_id: str, session: AsyncSession) -> bool:
        from sqlalchemy import delete
        await session.execute(delete(Message).where(Message.session_id == session_id))
        await session.execute(delete(ChatSession).where(ChatSession.id == session_id))
        await session.commit()
        return True


chat_service = ChatService()
