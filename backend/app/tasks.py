import time
import json
import asyncio

from app.celery_app import celery_app
from app.db import SessionLocal
from app.models import PRReview, AgentRun
from app.github_client import fetch_pr_diff, fetch_pr_files, post_review_comments
from app.graph import review_graph

from sqlalchemy.exc import IntegrityError
from app.models import Repo

@celery_app.task(name="review_pull_request", bind=True, max_retries=2)
def review_pull_request_task(self, installation_id, repo_full_name, pr_number, commit_sha):
    db = SessionLocal()

    # --- Idempotency guard: try to claim this commit for review ---
    review = PRReview(
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        commit_sha=commit_sha,
        status="running",
    )
    db.add(review)
    try:
        db.commit()
        db.refresh(review)
    except IntegrityError:
        db.rollback()
        print(f"Already processed {repo_full_name}#{pr_number}@{commit_sha[:7]} — skipping duplicate job")
        db.close()
        return

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        start = time.time()

        diff_text = loop.run_until_complete(fetch_pr_diff(installation_id, repo_full_name, pr_number))
        files_changed = loop.run_until_complete(fetch_pr_files(installation_id, repo_full_name, pr_number))
        repo_settings = db.query(Repo).filter(Repo.full_name == repo_full_name).first()
        enabled_agents = {
            "security": repo_settings.security_agent_enabled == "true" if repo_settings else True,
            "logic": repo_settings.logic_agent_enabled == "true" if repo_settings else True,
            "style": repo_settings.style_agent_enabled == "true" if repo_settings else True,
            "tests": repo_settings.tests_agent_enabled == "true" if repo_settings else True,
        }

        result = loop.run_until_complete(
            review_graph.ainvoke({
                "diff_text": diff_text,
                "files_changed": files_changed,
                "enabled_agents": enabled_agents,
                "findings": [],
            })
        )
        findings = result["findings"]

        duration_ms = int((time.time() - start) * 1000)

        for agent_name in ["security", "logic", "style", "tests"]:
            key = f"{agent_name}_findings"
            if key in result:
                db.add(AgentRun(
                    review_id=review.id,
                    agent_name=agent_name,
                    output_json=json.dumps(result[key]),
                    duration_ms=duration_ms,
                ))

        db.add(AgentRun(
            review_id=review.id,
            agent_name="critic",
            output_json=json.dumps(findings),
            duration_ms=duration_ms,
        ))

        loop.run_until_complete(
            post_review_comments(installation_id, repo_full_name, pr_number, commit_sha, findings)
        )

        review.status = "completed"
        db.commit()
        print(f"Review completed for {repo_full_name}#{pr_number} — {len(findings)} finding(s)")

    except Exception as e:
        print(f"Review task failed: {e}")
        review.status = "failed"
        db.commit()
        raise self.retry(exc=e, countdown=10)

    finally:
        db.close()