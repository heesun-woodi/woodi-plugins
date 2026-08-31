"""Validate fielded results against the drawn sample + response schema (Phase 2, step 3).

Encodes the UUID invariant AND the per-response schema check that the smoke test
showed is needed (a dispatch can return junk like "OK" instead of the answer JSON).

Two independent checks:
  1. INVARIANT (hard stop): results.json keys must be a subset of drawn_personas
     uuids. A key not in the drawn set = a fabricated/blended persona -> exit 2.
  2. COMPLETENESS + SCHEMA (re-dispatch, not fatal): report which drawn uuids have
     NO valid response yet — either missing entirely or present but failing the
     schema (required keys absent / wrong type). These slots should be re-fielded.

Usage
-----
    python validate_results.py \
        --drawn /run/drawn_personas.jsonl \
        --results /run/results.json \
        [--require A1,A2,B1,B2,D1,E1,E4]      # required keys (default: this set)

Exit codes: 0 = invariant holds AND every drawn uuid has a valid response.
            2 = invariant VIOLATED (fabricated uuid) — hard stop.
            3 = invariant holds but some slots need re-dispatch (see stderr list).
"""
from __future__ import annotations
import argparse, json, sys

DEFAULT_REQUIRED = ["A1", "A2", "B1", "B2", "D1", "E1", "E4"]


def valid_response(ans, required):
    if not isinstance(ans, dict):
        return False, "not an object"
    missing = [k for k in required if k not in ans or ans[k] in (None, "", [], {})]
    if missing:
        return False, f"missing/empty keys: {missing}"
    return True, ""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--drawn", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--require", default=",".join(DEFAULT_REQUIRED),
                    help="comma-separated required answer keys")
    args = ap.parse_args()
    required = [k.strip() for k in args.require.split(",") if k.strip()]

    drawn = [json.loads(l) for l in open(args.drawn) if l.strip()]
    drawn_uuids = {r["uuid"] for r in drawn}
    results = json.load(open(args.results))
    keys = set(results.keys())

    # --- Check 1: INVARIANT ---
    fabricated = keys - drawn_uuids
    if fabricated:
        print(f"INVARIANT VIOLATED — results contain uuids NOT in drawn sample "
              f"(fabricated/blended): {sorted(fabricated)}", file=sys.stderr)
        print("HARD STOP. Discard these responses; they were not drawn from the dataset.",
              file=sys.stderr)
        sys.exit(2)

    # --- Check 2: COMPLETENESS + SCHEMA ---
    need_redispatch = []
    for u in drawn_uuids:
        if u not in results:
            need_redispatch.append((u, "no response"))
            continue
        ok, why = valid_response(results[u], required)
        if not ok:
            need_redispatch.append((u, why))

    print(f"drawn={len(drawn_uuids)}  results={len(keys)}  "
          f"valid={len(drawn_uuids) - len(need_redispatch)}", file=sys.stderr)
    print("INVARIANT: results ⊆ drawn  ✓ (no fabricated uuids)", file=sys.stderr)

    if need_redispatch:
        print(f"\n{len(need_redispatch)} slot(s) need RE-DISPATCH:", file=sys.stderr)
        for u, why in need_redispatch:
            print(f"  {u}  — {why}", file=sys.stderr)
        # emit the uuids to stdout so a caller can capture them programmatically
        print("\n".join(u for u, _ in need_redispatch))
        sys.exit(3)

    print("ALL SLOTS VALID — Phase 2 field complete.", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
