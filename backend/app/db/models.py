"""
SQLAlchemy ORM models for all persistent entities.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


# ── Repository ───────────────────────────────────────────────────────────


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    languages: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    framework_info: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    repo_map: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    files: Mapped[list["File"]] = relationship(back_populates="repository", cascade="all, delete-orphan")
    indexing_jobs: Mapped[list["IndexingJob"]] = relationship(back_populates="repository", cascade="all, delete-orphan")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="repository", cascade="all, delete-orphan")


# ── File ─────────────────────────────────────────────────────────────────


class File(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    repository_id: Mapped[str] = mapped_column(String(32), ForeignKey("repositories.id"), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)  # repo-relative
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    repository: Mapped["Repository"] = relationship(back_populates="files")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="file", cascade="all, delete-orphan")


# ── Chunk ────────────────────────────────────────────────────────────────


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    file_id: Mapped[str] = mapped_column(String(32), ForeignKey("files.id"), nullable=False)
    repository_id: Mapped[str] = mapped_column(String(32), ForeignKey("repositories.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    symbol_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    start_line: Mapped[int] = mapped_column(Integer, default=0)
    end_line: Mapped[int] = mapped_column(Integer, default=0)
    parent_symbol: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    file: Mapped["File"] = relationship(back_populates="chunks")


# ── IndexingJob ──────────────────────────────────────────────────────────


class IndexingJob(Base):
    __tablename__ = "indexing_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    repository_id: Mapped[str] = mapped_column(String(32), ForeignKey("repositories.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    processed_files: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    skipped_chunks: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    repository: Mapped["Repository"] = relationship(back_populates="indexing_jobs")


# ── ChatSession ──────────────────────────────────────────────────────────


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    repository_id: Mapped[str] = mapped_column(String(32), ForeignKey("repositories.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    repository: Mapped["Repository"] = relationship(back_populates="chat_sessions")
    messages: Mapped[list["Message"]] = relationship(back_populates="session", cascade="all, delete-orphan")


# ── Message ──────────────────────────────────────────────────────────────


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    session_id: Mapped[str] = mapped_column(String(32), ForeignKey("chat_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    tool_calls_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


# ── Review ───────────────────────────────────────────────────────────────


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    repository_id: Mapped[str] = mapped_column(String(32), ForeignKey("repositories.id"), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    input_type: Mapped[str] = mapped_column(String(20), default="file")  # file, diff, paste
    input_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    findings_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ── Investigation ────────────────────────────────────────────────────────


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    repository_id: Mapped[str] = mapped_column(String(32), ForeignKey("repositories.id"), nullable=False)
    issue_description: Mapped[str] = mapped_column(Text, nullable=False)
    diagnosis_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    suggested_fix_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ── GeneratedPatch ───────────────────────────────────────────────────────


class GeneratedPatch(Base):
    __tablename__ = "generated_patches"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    repository_id: Mapped[str] = mapped_column(String(32), ForeignKey("repositories.id"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    diff_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    files_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, applied, rejected
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


# ── TestRun ──────────────────────────────────────────────────────────────


class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    repository_id: Mapped[str] = mapped_column(String(32), ForeignKey("repositories.id"), nullable=False)
    command: Mapped[str] = mapped_column(String(1024), nullable=False)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running, passed, failed, error
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
