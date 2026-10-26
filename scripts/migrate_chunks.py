import sqlite3
from pathlib import Path

db_path = Path("data/mentoros.db")
if db_path.exists():
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cols = [c[1] for c in cur.execute("PRAGMA table_info(chunks)").fetchall()]
    print("Initial columns:", cols)
    
    if "doc_slug" not in cols:
        print("Adding doc_slug...")
        cur.execute("ALTER TABLE chunks ADD COLUMN doc_slug TEXT NOT NULL DEFAULT ''")
    
    if "page_number" not in cols:
        print("Adding page_number...")
        cur.execute("ALTER TABLE chunks ADD COLUMN page_number INTEGER NOT NULL DEFAULT 1")
    
    # Backfill doc_slug and page_number from doc_id and unit_no if present
    if "doc_id" in cols and "unit_no" in cols:
        print("Backfilling doc_slug and page_number...")
        cur.execute("UPDATE chunks SET doc_slug = doc_id, page_number = unit_no WHERE doc_slug = ''")
    
    conn.commit()
    final_cols = [c[1] for c in cur.execute("PRAGMA table_info(chunks)").fetchall()]
    print("Final columns:", final_cols)
    conn.close()
    print("Migration finished successfully.")
else:
    print("Database does not exist yet.")
