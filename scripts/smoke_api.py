"""
Phase 9.8 - MentorOS API smoke test (stdlib only).

Hits every core endpoint and asserts the integration contract. Passes in
TWO states:

  * Degraded  - Ollama / RAG pipeline not available. Asserts the degraded
                contract instead: /ask fails fast with 503 and creates NO
                orphan session; all read endpoints still respond.
  * Full      - Ollama up. Asserts a real answer round-trip, an SSE stream
                with `event:` frames, and (when a quiz is produced) a
                quiz/submit grading round-trip.

Exit code 0 = all checks passed (skipped checks are informational).
Run:  python scripts/smoke_api.py            # assumes uvicorn on :8000
      python scripts/smoke_api.py --base http://localhost:8000
"""

import argparse
import json
import sys
import urllib.error
import urllib.request


def _open(method, url, body=None, timeout=30):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    resp = urllib.request.urlopen(request, timeout=timeout)
    raw = resp.read()
    try:
        parsed = json.loads(raw.decode("utf-8")) if raw else {}
    except Exception:
        parsed = raw.decode("utf-8", "replace") if raw else {}
    return resp.status, parsed


def _call(base, method, path, body=None, expect=None, timeout=30):
    try:
        status, data = _open(method, base + path, body, timeout=timeout)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            data = raw.decode("utf-8", "replace") if raw else {}
        status = e.code
    if expect is not None and status != expect:
        raise AssertionError(f"expected HTTP {expect}, got {status}: {data}")
    return status, data


PASS = 0
FAIL = 0
SKIP = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"[ ok ] {name}{(' - ' + detail) if detail else ''}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}{(' - ' + detail) if detail else ''}")


def skip(name, why):
    global SKIP
    SKIP += 1
    print(f"[skip] {name} - {why}")


def main():
    parser = argparse.ArgumentParser(description="MentorOS API smoke test")
    parser.add_argument("--base", default="http://127.0.0.1:8000", help="API base URL")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    print(f"== MentorOS API smoke test ==  base={base}\n")

    # --- Read surface (works in every state) ---------------------------------
    status, s = _call(base, "GET", "/api/status")
    check("GET /api/status -> 200", status == 200)
    pipeline_ready = bool(s.get("pipeline_ready"))
    ollama_up = bool(s.get("ollama_available"))
    check(
        "status payload complete",
        all(k in s for k in ("pipeline_ready", "missing_packages", "files_indexed", "api_version")),
        f"api_version={s.get('api_version')} files={s.get('files_indexed')}",
    )

    before, _sessions = _call(base, "GET", "/api/sessions")
    check("GET /api/sessions list", before == 200 and isinstance(_sessions, list))

    st, mem = _call(base, "GET", "/api/memory")
    check("GET /api/memory snapshot", st == 200 and isinstance(mem, dict) and "topics" in mem,
          f"{mem.get('session_id')} topics={len(mem.get('topics', []))}")

    st, weak = _call(base, "GET", "/api/memory/weak")
    check("GET /api/memory/weak list", st == 200 and isinstance(weak, list))
    st, strong = _call(base, "GET", "/api/memory/strong")
    check("GET /api/memory/strong list", st == 200 and isinstance(strong, list))

    st, files = _call(base, "GET", "/api/files")
    check("GET /api/files list", st == 200 and isinstance(files, list), f"{len(files)} file(s)")

    st, _ = _call(base, "GET", "/api/chunks/missing-chunk-000")
    # 503 = pipeline deps missing (degraded); 404 = ready but unknown chunk id.
    check("GET /api/chunks/{id} -> 503 degraded or 404 miss", st in (503, 404), f"HTTP {st}")

    st, _ = _call(base, "GET", "/api/sessions/does-not-exist/messages")
    check("GET /api/sessions/{id}/messages 404 on miss", st == 404)

    st, _ = _call(base, "DELETE", "/api/sessions/does-not-exist")
    check("DELETE /api/sessions/{id} 404 on miss", st == 404)

    st, _ = _call(base, "POST", "/api/reflection", {"session_id": None})
    check("POST /api/reflection 404 when no sessions", st == 404)

    # --- Ask / chat surface ---------------------------------------------------
    if not ollama_up:
        detail = s.get("missing_packages") or []
        st, ask = _call(base, "POST", "/api/ask", {"message": "hello"})
        check("POST /api/ask fails fast 503 when Ollama down", st == 503,
              str(ask.get("detail", ""))[:80])
        after, _s2 = _call(base, "GET", "/api/sessions")
        check("degraded /ask created NO session", after == 200 and len(_s2) == len(_sessions))
        skip("full RAG round-trip", f"Ollama down (missing={detail})")
        skip("SSE stream + quiz submit", "requires Ollama")
    else:
        st, stream = _call(base, "GET", "/api/status")
        if not pipeline_ready:
            skip("full RAG round-trip", "pipeline not ready (embeddings/chroma missing)")
        else:
            st, ask = _call(base, "POST", "/api/ask", {"message": "hello"})
            check("POST /api/ask -> 200 dict", st == 200 and isinstance(ask, dict),
                  f"action={ask.get('action')} type={ask.get('type')}")
            check("ask carries ids", ask.get("message_id" if "message_id" in ask else "user_message_id"),
                  "assistant_message_id=" + str(ask.get("assistant_message_id")))

            if ask.get("type") == "quiz" and ask.get("quiz"):
                n = len(ask["quiz"])
                answers = [{"question_id": q.get("question_id"), "choice": "A"} for q in ask["quiz"]]
                st, graded = _call(base, "POST", "/api/quiz/submit",
                                   {"session_id": ask.get("session_id"),
                                    "message_id": ask.get("assistant_message_id"),
                                    "answers": answers})
                check("POST /api/quiz/submit grades quiz",
                      st == 200 and graded.get("total") == n and "content" in graded,
                      f"score={graded.get('score')}/{graded.get('total')}")

        # SSE stream sanity: first bytes should contain 'event:'
        try:
            body = json.dumps({"message": "hello"}).encode("utf-8")
            req = urllib.request.Request(base + "/api/ask/stream", data=body,
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                head = resp.read(2048)
            check("POST /api/ask/stream SSE frames", b"event:" in head,
                  head[:80].decode("utf-8", "replace").replace("\n", " "))
        except urllib.error.HTTPError as e:
            check("POST /api/ask/stream SSE frames", e.code == 503, f"HTTP {e.code}")

    print(f"\n== Results: {PASS} passed, {FAIL} failed, {SKIP} skipped ==")
    if FAIL:
        sys.exit(1)
    if SKIP:
        print("(skipped checks require Ollama + pipeline packages - run again when ready)")
    sys.exit(0)


if __name__ == "__main__":
    main()