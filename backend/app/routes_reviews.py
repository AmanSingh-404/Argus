from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json

from app.db import get_db
from app.models import PRReview, AgentRun

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