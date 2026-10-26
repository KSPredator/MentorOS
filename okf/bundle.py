"""
OKF Bundle and Concept IO / Conformance checks (pure code, no LLM).
Conforms to OKF v0.2 specification:
    - load_concept
    - write_concept
    - trust_tier
    - is_stale
    - check_bundle
    - regen_index
    - append_log
    - init_bundle
"""

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import yaml

from okf.models import Concept

RESERVED_FILES = {"index.md", "log.md"}


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extract YAML frontmatter and markdown body from file content."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    raw_yaml = parts[1]
    body = parts[2].lstrip("\r\n")

    try:
        data = yaml.safe_load(raw_yaml) or {}
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}

    return data, body


def load_concept(path: Union[str, Path]) -> Concept:
    """Parse frontmatter and body from a markdown concept file. Unknown keys preserved."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Concept file not found: {p}")

    text = p.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)

    # Concept id is the relative path without .md
    cid = p.stem
    return Concept(id=cid, meta=meta, body=body, file_path=str(p.resolve()))


def write_concept(
    concept: Concept,
    dest_path: Optional[Union[str, Path]] = None,
    bundle_root: Optional[Union[str, Path]] = None,
) -> Path:
    """Write concept to file with YAML frontmatter preserving all keys."""
    if dest_path:
        out_path = Path(dest_path)
    elif bundle_root:
        out_path = Path(bundle_root) / f"{concept.id}.md"
    elif concept.file_path:
        out_path = Path(concept.file_path)
    else:
        raise ValueError("Must provide dest_path, bundle_root, or concept.file_path.")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Dump YAML frontmatter
    yaml_str = yaml.dump(
        concept.meta,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    content = f"---\n{yaml_str}---\n\n{concept.body.strip()}\n"
    out_path.write_text(content, encoding="utf-8")
    concept.file_path = str(out_path.resolve())
    return out_path


def trust_tier(concept: Concept) -> str:
    """
    Derive trust tier per OKF v0.2 spec:
    - 'unverified': no verified entries
    - 'human-reviewed': any verified entry has by starting with 'human:'
    - 'machine-confirmed': verified exists with non-human verifiers
    """
    verified = concept.verified
    if not verified:
        return "unverified"

    for entry in verified:
        verifier = str(entry.get("by", "")).lower()
        if verifier.startswith("human:"):
            return "human-reviewed"

    return "machine-confirmed"


def is_stale(concept: Concept, now: Optional[datetime] = None) -> bool:
    """
    Check if concept has expired based on stale_after field.
    Absent status or status != 'deprecated' is assumed stable unless now >= stale_after.
    """
    stale_date_str = concept.stale_after
    if not stale_date_str:
        return False

    current_time = now or datetime.now(timezone.utc)
    try:
        # Support ISO 8601 strings (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        clean_str = stale_date_str.replace("Z", "+00:00")
        if "T" in clean_str:
            stale_dt = datetime.fromisoformat(clean_str)
        else:
            stale_dt = datetime.fromisoformat(clean_str).replace(tzinfo=timezone.utc)
        return current_time >= stale_dt
    except Exception:
        return False


def check_bundle(bundle_root: Union[str, Path]) -> List[str]:
    """
    Validate OKF v0.2 bundle conformance:
    - Root index.md must exist and have frontmatter with okf_version == '0.2'
    - Every non-reserved .md file must have parseable frontmatter and non-empty 'type'
    Tolerates broken links and missing intermediate indexes per spec.
    """
    root = Path(bundle_root)
    errors: List[str] = []

    if not root.exists() or not root.is_dir():
        return [f"Bundle root does not exist or is not a directory: {root}"]

    root_index = root / "index.md"
    if not root_index.exists():
        errors.append(f"Missing root index.md at {root}")
    else:
        text = root_index.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(text)
        if str(meta.get("okf_version")) != "0.2":
            errors.append(f"Root index.md missing 'okf_version: \"0.2\"' frontmatter.")

    for md_file in root.rglob("*.md"):
        rel_path = md_file.relative_to(root).as_posix()
        if md_file.name in RESERVED_FILES:
            continue

        try:
            text = md_file.read_text(encoding="utf-8")
            meta, _ = parse_frontmatter(text)
            if not meta:
                errors.append(f"{rel_path}: Missing YAML frontmatter.")
            elif not meta.get("type"):
                errors.append(f"{rel_path}: Missing required 'type' field in frontmatter.")
        except Exception as e:
            errors.append(f"{rel_path}: Failed to parse: {e}")

    return errors


def regen_index(dir_path: Union[str, Path]) -> Path:
    """
    Generate or regenerate directory index.md with entries:
    * [Title](relative_path.md) - description
    """
    p = Path(dir_path)
    index_file = p / "index.md"

    # Preserve existing frontmatter if present (especially root okf_version: "0.2")
    existing_meta = {}
    if index_file.exists():
        existing_meta, _ = parse_frontmatter(index_file.read_text(encoding="utf-8"))

    md_files = sorted(
        [f for f in p.glob("*.md") if f.name not in RESERVED_FILES],
        key=lambda x: x.name,
    )

    lines = []
    if existing_meta:
        yaml_str = yaml.dump(existing_meta, sort_keys=False, default_flow_style=False)
        lines.append(f"---\n{yaml_str}---\n")

    lines.append(f"# {p.name.replace('-', ' ').title()}\n")
    for f in md_files:
        try:
            c = load_concept(f)
            desc = f" - {c.description}" if c.description else ""
            lines.append(f"* [{c.title}]({f.name}){desc}")
        except Exception:
            lines.append(f"* [{f.stem}]({f.name})")

    index_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index_file


def append_log(bundle_root: Union[str, Path], kind: str, text: str) -> None:
    """
    Prepend a dated entry (## YYYY-MM-DD) newest first to log.md.
    """
    root = Path(bundle_root)
    log_file = root / "log.md"
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    entry = f"## {today_str}\n\n* **[{kind}]** {text.strip()}\n\n"

    if log_file.exists():
        existing = log_file.read_text(encoding="utf-8")
        # If today header already exists at top, merge
        if existing.startswith(f"## {today_str}\n"):
            header_end = existing.find("\n\n")
            rest = existing[header_end + 2:]
            new_content = f"## {today_str}\n\n* **[{kind}]** {text.strip()}\n{rest}"
        else:
            new_content = entry + existing
    else:
        new_content = f"# Knowledge Bundle Change Log\n\n{entry}"

    log_file.write_text(new_content, encoding="utf-8")


def init_bundle(bundle_dir: Union[str, Path], course_name: str = "Course Knowledge") -> Path:
    """Initialize a compliant OKF v0.2 bundle skeleton."""
    b_path = Path(bundle_dir)
    b_path.mkdir(parents=True, exist_ok=True)
    (b_path / "references").mkdir(parents=True, exist_ok=True)

    index_file = b_path / "index.md"
    if not index_file.exists():
        index_content = (
            "---\n"
            "okf_version: \"0.2\"\n"
            f"title: \"{course_name}\"\n"
            "type: \"Course\"\n"
            "---\n\n"
            f"# {course_name}\n\n"
            "Open Knowledge Format (OKF v0.2) curated course repository.\n"
        )
        index_file.write_text(index_content, encoding="utf-8")

    log_file = b_path / "log.md"
    if not log_file.exists():
        append_log(b_path, "INITIALIZE", f"Created OKF bundle for '{course_name}'.")

    return b_path
