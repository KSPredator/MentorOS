"""
Unit tests for okf library conforming to Step 4 of the roadmap.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import tempfile
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from okf import (
    Concept,
    load_concept,
    write_concept,
    trust_tier,
    is_stale,
    check_bundle,
    regen_index,
    append_log,
    init_bundle,
    extract_links,
    build_graph,
)


def test_okf():
    print("Testing okf/ library...")
    with tempfile.TemporaryDirectory() as tmpdir:
        bundle_root = Path(tmpdir) / "bundle" / "test-course"
        init_bundle(bundle_root, course_name="Test Operating Systems")

        # 1. Test check_bundle on fresh skeleton
        errors = check_bundle(bundle_root)
        assert len(errors) == 0, f"Expected 0 errors on fresh bundle, got {errors}"
        print("  -> check_bundle on initial skeleton passed!")

        # 2. Test concept write & load (with unknown frontmatter preservation)
        concept = Concept(
            id="paging",
            meta={
                "title": "Virtual Memory Paging",
                "type": "Concept",
                "description": "Fixed size block translation scheme.",
                "status": "stable",
                "stale_after": (datetime.now(timezone.utc) + timedelta(days=90)).strftime("%Y-%m-%d"),
                "sources": [{"id": "os-p41-c0", "title": "OS Unit 3 (Page 41)"}],
                "custom_unknown_key": "must_be_preserved_per_spec",
                "verified": [{"by": "human:prof_smith", "at": "2026-10-16T12:00:00Z"}],
            },
            body="Paging divides memory into frames [^os-p41-c0]. See also [Segmentation](segmentation.md).\n",
        )
        written_path = write_concept(concept, bundle_root=bundle_root)
        assert written_path.exists()

        loaded = load_concept(written_path)
        assert loaded.title == "Virtual Memory Paging"
        assert loaded.meta.get("custom_unknown_key") == "must_be_preserved_per_spec"
        assert trust_tier(loaded) == "human-reviewed"
        assert not is_stale(loaded)
        print("  -> load_concept, write_concept, unknown key preservation passed!")

        # 3. Test trust_tier machine-confirmed & unverified
        unverified_c = Concept(id="uv", meta={"type": "Concept"}, body="")
        assert trust_tier(unverified_c) == "unverified"

        machine_c = Concept(id="mc", meta={"type": "Concept", "verified": {"by": "process:eval_agent", "at": "now"}}, body="")
        assert trust_tier(machine_c) == "machine-confirmed"
        print("  -> trust_tier derivation passed!")

        # 4. Test stale check
        stale_c = Concept(id="stale", meta={"type": "Concept", "stale_after": "2020-01-01"}, body="")
        assert is_stale(stale_c) is True
        print("  -> is_stale check passed!")

        # 5. Test link extraction and graph building
        c2 = Concept(
            id="segmentation",
            meta={"title": "Segmentation", "type": "Concept"},
            body="Variable size memory blocks. Contrasted with [Paging](paging.md).\n",
        )
        write_concept(c2, bundle_root=bundle_root)

        links = extract_links(loaded)
        assert "segmentation" in links

        G = build_graph(bundle_root)
        assert G.number_of_nodes() >= 2
        assert G.has_edge("paging", "segmentation")
        print("  -> extract_links and build_graph passed!")

        # 6. Test regen_index & append_log
        regen_index(bundle_root)
        append_log(bundle_root, "VERIFY", "Human verification applied to paging.")
        log_content = (bundle_root / "log.md").read_text(encoding="utf-8")
        assert "Human verification" in log_content
        print("  -> regen_index and append_log passed!")

        # 7. Final check_bundle
        errors = check_bundle(bundle_root)
        assert len(errors) == 0, f"Unexpected bundle errors: {errors}"
        print("  -> check_bundle on populated bundle passed with 0 errors!")

    print("\nALL OKF LIBRARY TESTS PASSED!")


if __name__ == "__main__":
    test_okf()
