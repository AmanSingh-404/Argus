from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.sql import func
from app.db import Base


class PRReview(Base):
    __tablename__ = "pr_reviews"
    __table_args__ = (
        UniqueConstraint("repo_full_name", "pr_number", "commit_sha", name="uq_repo_pr_commit"),
    )

    id = Column(Integer, primary_key=True)
    repo_full_name = Column(String, nullable=False)
    pr_number = Column(Integer, nullable=False)
    commit_sha = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, running, completed, failed
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("pr_reviews.id"), nullable=False)
    agent_name = Column(String, nullable=False)
    output_json = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DocIndex(Base):
    __tablename__ = "doc_index"

    id = Column(Integer, primary_key=True)
    repo_full_name = Column(String, nullable=False)
    source_path = Column(String, nullable=False)
    doc_path = Column(String, nullable=False)
    last_synced_commit_sha = Column(String, nullable=True)


class DocsPR(Base):
    __tablename__ = "docs_prs"

    id = Column(Integer, primary_key=True)
    repo_full_name = Column(String, nullable=False)
    doc_path = Column(String, nullable=True)
    pr_number = Column(Integer, nullable=True)
    trigger = Column(String, nullable=False)  # "push" or "scheduled"
    source_commit_sha = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, opened, failed
    opened_at = Column(DateTime(timezone=True), server_default=func.now())