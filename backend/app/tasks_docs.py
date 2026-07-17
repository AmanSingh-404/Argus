import asyncio
import time
from app.celery_app import celery_app
from app.db import SessionLocal
from app.models import DocIndex, DocsPR
from app.github_client import (
    fetch_commit_diff,
    fetch_file_content,
    create_branch,
    commit_file_update,
    open_pull_request,
)
from app.docs_agent import draft_doc_update, self_check_draft


@celery_app.task(name="process_push_event")
def process_push_event_task(installation_id, repo_full_name, before_sha, after_sha, changed_files):
    db = SessionLocal()
    mappings = db.query(DocIndex).filter(DocIndex.repo_full_name == repo_full_name).all()
    relevant = [m for m in mappings if m.source_path in changed_files]

    if not relevant:
        print(f"No indexed docs affected by this push (changed: {changed_files})")
        db.close()
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    diff_text = loop.run_until_complete(fetch_commit_diff(installation_id, repo_full_name, before_sha, after_sha))

    for m in relevant:
        print(f"Drift candidate: {m.source_path} -> {m.doc_path}")
        current_doc = loop.run_until_complete(fetch_file_content(installation_id, repo_full_name, m.doc_path))

        draft = loop.run_until_complete(draft_doc_update(current_doc, diff_text))
        check = loop.run_until_complete(self_check_draft(draft, diff_text))
        print(f"Self-check result: {check}")

        if draft.strip() == current_doc.strip():
            print(f"Draft is identical to current doc — no real change needed, skipping PR")
            continue

        if not check.get("confident"):
            print(f"Self-check not confident — skipping PR. Issues: {check.get('issues')}")
            docs_pr = DocsPR(
                repo_full_name=repo_full_name,
                trigger="push",
                source_commit_sha=after_sha,
                status="failed",
            )
            db.add(docs_pr)
            db.commit()
            continue

        branch_name = f"argus-docs-update-{after_sha[:7]}-{int(time.time())}"

        try:
            loop.run_until_complete(create_branch(installation_id, repo_full_name, branch_name, after_sha))
            loop.run_until_complete(commit_file_update(
                installation_id, repo_full_name, branch_name, m.doc_path, draft,
                commit_message=f"docs: update {m.doc_path} for changes in {m.source_path}",
            ))
            pr = loop.run_until_complete(open_pull_request(
                installation_id, repo_full_name,
                title=f"docs: update {m.doc_path} to match {m.source_path}",
                body=(
                    f"Argus detected that recent changes to `{m.source_path}` may have made "
                    f"`{m.doc_path}` outdated, and drafted this update.\n\n"
                    f"**Source commit:** {after_sha}\n\n"
                    f"This PR was opened automatically and has not been merged — please review "
                    f"before merging."
                ),
                head_branch=branch_name,
            ))
            print(f"Opened docs PR #{pr['number']}: {pr['html_url']}")

            db.add(DocsPR(
                repo_full_name=repo_full_name,
                pr_number=pr["number"],
                trigger="push",
                source_commit_sha=after_sha,
                status="opened",
            ))
            db.commit()

        except Exception as e:
            print(f"Failed to open docs PR: {e}")
            db.add(DocsPR(
                repo_full_name=repo_full_name,
                trigger="push",
                source_commit_sha=after_sha,
                status="failed",
            ))
            db.commit()

    db.close()