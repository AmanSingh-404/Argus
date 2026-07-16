import asyncio
from app.db import SessionLocal
from app.models import DocIndex
from app.doc_indexer import build_doc_index

# --- Fill these in for your test repo ---
INSTALLATION_ID = 145805684  # from your earlier logs
REPO_FULL_NAME = "AmanSingh-404/argus-test-repo"


async def main():
    mappings = await build_doc_index(INSTALLATION_ID, REPO_FULL_NAME)
    print(f"Proposed mappings: {mappings}")

    db = SessionLocal()
    for m in mappings:
        db.add(DocIndex(
            repo_full_name=REPO_FULL_NAME,
            source_path=m["source_path"],
            doc_path=m["doc_path"],
        ))
    db.commit()
    db.close()
    print(f"Saved {len(mappings)} mapping(s) to doc_index.")


if __name__ == "__main__":
    asyncio.run(main())