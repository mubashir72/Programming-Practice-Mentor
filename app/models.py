from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class Learner(Base):
    __tablename__ = "learners"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    language: Mapped[str] = mapped_column(String(30), default="python")
    skill_level: Mapped[str] = mapped_column(String(30), default="beginner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Exercise(Base):
    __tablename__ = "exercises"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(30), default="python")
    topic: Mapped[str] = mapped_column(String(80))
    difficulty: Mapped[str] = mapped_column(String(30))
    starter_code: Mapped[str] = mapped_column(Text)
    tests: Mapped[list] = mapped_column(JSON)
    target_errors: Mapped[list] = mapped_column(JSON, default=list)


class SessionState(Base):
    __tablename__ = "session_states"
    id: Mapped[int] = mapped_column(primary_key=True)
    learner_id: Mapped[int] = mapped_column(ForeignKey("learners.id"), index=True)
    exercise_id: Mapped[Optional[int]] = mapped_column(ForeignKey("exercises.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    current_plan: Mapped[dict] = mapped_column(JSON, default=dict)
    checkpoint: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = (UniqueConstraint("learner_id", "idempotency_key", name="uq_attempt_retry"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    learner_id: Mapped[int] = mapped_column(ForeignKey("learners.id"), index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("session_states.id"))
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    code: Mapped[str] = mapped_column(Text)
    result: Mapped[dict] = mapped_column(JSON)
    idempotency_key: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ErrorEvent(Base):
    __tablename__ = "error_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    learner_id: Mapped[int] = mapped_column(ForeignKey("learners.id"), index=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id"))
    category: Mapped[str] = mapped_column(String(80))
    topic: Mapped[str] = mapped_column(String(80))
    confidence: Mapped[float] = mapped_column(default=0.0)
    evidence: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id"))
    text: Mapped[str] = mapped_column(Text)
    plan: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MemoryEvent(Base):
    __tablename__ = "memory_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    learner_id: Mapped[int] = mapped_column(ForeignKey("learners.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
    source_reference: Mapped[str] = mapped_column(String(200), default="application")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LearnerFact(Base):
    __tablename__ = "learner_facts"
    id: Mapped[int] = mapped_column(primary_key=True)
    learner_id: Mapped[int] = mapped_column(ForeignKey("learners.id"), index=True)
    fact_type: Mapped[str] = mapped_column(String(80))
    fact_value: Mapped[str] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="current")
    supersedes_id: Mapped[Optional[int]] = mapped_column(ForeignKey("learner_facts.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
