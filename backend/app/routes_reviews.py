from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json

from app.db import get_db
from app.models import PRReview, AgentRun
from app.models import DocsPR
from app.models import Repo

router = APIRouter()


@router.get("/reviews")
def list_reviews(db: Session = Depends(get_db)):
    reviews = db.query(PRReview).order_by(desc(PRReview.opened_at)).limit(50).all()
    return [
        {
            "id": r.id,
            "repo_full_name": r.repo_full_name,
            "pr_number": r.pr_number,
            "commit_sha": r.commit_sha,
            "status": r.status,
            "opened_at": r.opened_at.isoformat() if r.opened_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in reviews
    ]


@router.get("/reviews/{review_id}")
def get_review(review_id: int, db: Session = Depends(get_db)):
    review = db.query(PRReview).filter(PRReview.id == review_id).first()
    if not review:
        return {"error": "not found"}

    agent_runs = db.query(AgentRun).filter(AgentRun.review_id == review_id).all()

    return {
        "id": review.id,
        "repo_full_name": review.repo_full_name,
        "pr_number": review.pr_number,
        "commit_sha": review.commit_sha,
        "status": review.status,
        "opened_at": review.opened_at.isoformat() if review.opened_at else None,
        "agent_runs": [
            {
                "agent_name": ar.agent_name,
                "findings": json.loads(ar.output_json) if ar.output_json else [],
                "duration_ms": ar.duration_ms,
            }
            for ar in agent_runs
        ],
    }

@router.get("/docs-prs")
def list_docs_prs(db: Session = Depends(get_db)):
    prs = db.query(DocsPR).order_by(desc(DocsPR.opened_at)).limit(50).all()
    return [
        {
            "id": p.id,
            "repo_full_name": p.repo_full_name,
            "doc_path": p.doc_path,
            "pr_number": p.pr_number,
            "trigger": p.trigger,
            "source_commit_sha": p.source_commit_sha,
            "status": p.status,
            "opened_at": p.opened_at.isoformat() if p.opened_at else None,
        }
        for p in prs
    ]

@router.get("/repos")
def list_repos(db: Session = Depends(get_db)):
    repos = db.query(Repo).all()
    return [
        {
            "id": r.id,
            "full_name": r.full_name,
            "security_agent_enabled": r.security_agent_enabled == "true",
            "logic_agent_enabled": r.logic_agent_enabled == "true",
            "style_agent_enabled": r.style_agent_enabled == "true",
            "tests_agent_enabled": r.tests_agent_enabled == "true",
            "docs_agent_enabled": r.docs_agent_enabled == "true",
        }
        for r in repos
    ]


@router.patch("/repos/{repo_id}")
def update_repo_settings(repo_id: int, settings: dict, db: Session = Depends(get_db)):
    repo = db.query(Repo).filter(Repo.id == repo_id).first()
    if not repo:
        return {"error": "not found"}

    for field in ["security_agent_enabled", "logic_agent_enabled", "style_agent_enabled", "tests_agent_enabled", "docs_agent_enabled"]:
        if field in settings:
            setattr(repo, field, "true" if settings[field] else "false")

    db.commit()
    return {"status": "updated"}