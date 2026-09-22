"""
Dataset Builder for Phase 8 Evaluation
======================================
Parses qa.txt into structured JSON benchmark (data/eval_qa.json)
and indexes the course notes into ChromaDB VectorStore.
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from embeddings import get_vector_store
from ingestion.parser import ParsedPage
from ingestion.chunker import chunk_document
QA_TXT_PATH = PROJECT_ROOT / "qa.txt"
EVAL_JSON_PATH = PROJECT_ROOT / "data" / "eval_qa.json"
COURSE_NOTES_PATH = PROJECT_ROOT / "data" / "ai_engineering_course_notes.txt"


# Unanswerable / out-of-domain distractor questions for hallucination testing
DISTRACTORS = [
    {
        "id": "qa_distractor_1",
        "chapter": "Out of Domain / Distractor",
        "question": "What is the boiling point of liquid nitrogen at standard atmospheric pressure?",
        "ground_truth": "I don't have enough information in the uploaded documents to answer this.",
        "is_answerable": False,
    },
    {
        "id": "qa_distractor_2",
        "chapter": "Out of Domain / Distractor",
        "question": "How do you prepare traditional Italian sourdough pasta dough from scratch?",
        "ground_truth": "I don't have enough information in the uploaded documents to answer this.",
        "is_answerable": False,
    },
    {
        "id": "qa_distractor_3",
        "chapter": "Out of Domain / Distractor",
        "question": "What are the key differences between Mitochondria and Chloroplasts in plant cells?",
        "ground_truth": "I don't have enough information in the uploaded documents to answer this.",
        "is_answerable": False,
    },
    {
        "id": "qa_distractor_4",
        "chapter": "Out of Domain / Distractor",
        "question": "Who was the prime minister of the United Kingdom during the Battle of Waterloo in 1815?",
        "ground_truth": "I don't have enough information in the uploaded documents to answer this.",
        "is_answerable": False,
    },
    {
        "id": "qa_distractor_5",
        "chapter": "Out of Domain / Distractor",
        "question": "What are the rules and scoring regulations of cricket regarding a super over?",
        "ground_truth": "I don't have enough information in the uploaded documents to answer this.",
        "is_answerable": False,
    },
]


def parse_qa_file(file_path: Path = QA_TXT_PATH) -> List[Dict[str, Any]]:
    """Parse qa.txt into structured list of QA items."""
    text = file_path.read_text(encoding="utf-8")
    lines = text.split("\n")
    
    current_chapter = "General AI Engineering"
    items = []
    
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
            
        if line_str.startswith("###"):
            current_chapter = line_str.lstrip("#").strip()
            continue
            
        # Match pattern: 1. **Question?** Answer.
        match = re.match(r"^(\d+)\.\s*\*\*(.*?)\*\*\s*(.*)$", line_str)
        if match:
            num = match.group(1)
            q = match.group(2).strip()
            a = match.group(3).strip()
            items.append({
                "id": f"qa_{num}",
                "num": int(num),
                "chapter": current_chapter,
                "question": q,
                "ground_truth": a,
                "is_answerable": True,
            })
            
    # Add distractor items
    for d in DISTRACTORS:
        items.append(d)
        
    return items


def create_course_notes_doc(items: List[Dict[str, Any]]) -> str:
    """Generate structured course text from the QA knowledge base for indexing."""
    chapters: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        if not item.get("is_answerable", True):
            continue
        ch = item.get("chapter", "General")
        chapters.setdefault(ch, []).append(item)
        
    sections = []
    for ch_name, ch_items in chapters.items():
        sec_lines = [f"# {ch_name}\n"]
        for it in ch_items:
            sec_lines.append(f"Topic: {it['question']}")
            sec_lines.append(f"Explanation: {it['ground_truth']}\n")
        sections.append("\n".join(sec_lines))
        
    return "\n\n---\n\n".join(sections)


def build_and_index_dataset():
    """Main execution function."""
    print("1. Parsing qa.txt...")
    items = parse_qa_file()
    print(f"   Parsed {len(items)} QA items ({len(items) - len(DISTRACTORS)} answerable + {len(DISTRACTORS)} distractors).")
    
    # Save JSON dataset
    EVAL_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EVAL_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"2. Saved structured dataset to {EVAL_JSON_PATH}")
    
    # Generate and save text notes
    notes_text = create_course_notes_doc(items)
    with open(COURSE_NOTES_PATH, "w", encoding="utf-8") as f:
        f.write(notes_text)
    print(f"3. Generated course notes at {COURSE_NOTES_PATH}")
    
    # Index notes into ChromaDB
    print("4. Indexing course notes into ChromaDB...")
    page = ParsedPage(
        text=notes_text,
        page_number=1,
        source_file="ai_engineering_course_notes.txt",
        metadata={"title": "AI Engineering Course Notes"},
    )
    chunks = chunk_document([page])
    vs = get_vector_store()
    indexed = vs.add_chunks(chunks)
    print(f"   Successfully indexed {indexed} chunks into ChromaDB (Total in DB: {vs.count()})")
    
    return items, chunks


if __name__ == "__main__":
    build_and_index_dataset()
