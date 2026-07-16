import asyncio
from app.celery_app import celery_app
from app.db import SessionLocal
from app.models import DocIndex
from app.github_client import fetch_commit_diff, fetch_file_content
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
        print(f"--- DRAFT for {m.doc_path} ---\n{draft}\n--- END DRAFT ---")

    db.close()