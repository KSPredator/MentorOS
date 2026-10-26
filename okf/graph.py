"""
OKF Knowledge Graph module using NetworkX.
Builds directed graph over concept markdown links.
"""

from pathlib import Path
import re
from typing import Dict, List, Set, Tuple, Union
import networkx as nx

from okf.bundle import load_concept, RESERVED_FILES
from okf.models import Concept


def extract_links(concept: Concept) -> List[str]:
    """
    Extract Markdown links targeting other concept files.
    Matches [text](path.md) or [text](/path.md).
    Returns list of normalized concept IDs without .md extension.
    """
    pattern = r"\[([^\]]+)\]\(([^)]+\.md)\)"
    matches = re.findall(pattern, concept.body)

    target_concepts: List[str] = []
    for _, target_path in matches:
        clean = target_path.strip().lstrip("/")
        if clean in RESERVED_FILES or clean.endswith("index.md"):
            continue
        cid = clean[:-3] if clean.endswith(".md") else clean
        target_concepts.append(cid)

    return target_concepts


def build_graph(bundle_root: Union[str, Path]) -> nx.DiGraph:
    """
    Construct a NetworkX DiGraph representing the Knowledge Map of the course bundle.
    Nodes: concept IDs with title, trust_tier, status, tags
    Edges: directed link references between concepts
    """
    root = Path(bundle_root)
    G = nx.DiGraph()

    concepts: Dict[str, Concept] = {}
    for md_file in root.rglob("*.md"):
        if md_file.name in RESERVED_FILES:
            continue
        try:
            c = load_concept(md_file)
            rel_cid = md_file.relative_to(root).as_posix()
            if rel_cid.endswith(".md"):
                rel_cid = rel_cid[:-3]
            c.id = rel_cid
            concepts[c.id] = c
            G.add_node(
                c.id,
                title=c.title,
                description=c.description,
                type=c.concept_type,
                status=c.status,
                trust_tier=c.meta.get("trust_tier", "unverified"),
                tags=c.meta.get("tags", []),
            )
        except Exception:
            continue

    for cid, c in concepts.items():
        links = extract_links(c)
        for target in links:
            # Find matching concept
            if target in concepts:
                G.add_edge(cid, target)
            else:
                # Resolve relative or bare name
                target_base = target.split("/")[-1]
                for candidate_id in concepts:
                    if candidate_id.split("/")[-1] == target_base:
                        G.add_edge(cid, candidate_id)
                        break

    return G
