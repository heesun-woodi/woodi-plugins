"""Batch-draw N real personas for a run (Phase 2, step 1).

WHY THIS EXISTS: the dataset skill's load_persona.py draws exactly ONE row
(hits.sample(n=1, random_state=seed)). A find-the-ICP run needs N rows in one
dataset load. This helper mirrors that sampling (same filter grammar, same
random_state semantics) but draws N, writing drawn_personas.jsonl — the origin
of the UUID spine. Every row here is a REAL row; never hand-write personas.

Usage
-----
    python draw_personas.py \
        --filter "age>=25,age<=45" \
        --n 8 --seed 42 \
        --out /path/to/run/drawn_personas.jsonl

Filter grammar (same as load_persona.py): comma-separated clauses —
  col=val | col>=n | col<=n | col!=val | xsubstr=<text>
Field-semantics quirks (from the dataset skill): `province` is abbreviated
(서울, 경기, 전북 doubly-shortened vs 전라남); `district` already carries the
province prefix — never combine province+district in one injected string.
"""
from __future__ import annotations
import argparse, json, sys, operator

REPO = "nvidia/Nemotron-Personas-Korea"

# columns for fielding + ICP demographic fit; interview reloads full narrative by uuid.
DEFAULT_COLS = ["uuid", "sex", "age", "province", "district", "education_level",
                "marital_status", "family_type", "housing_type", "occupation", "persona"]

OPS = {">=": operator.ge, "<=": operator.le, "!=": operator.ne, "=": operator.eq}


def apply_clause(df, clause):
    for op in (">=", "<=", "!=", "="):          # longest ops first
        if op in clause:
            col, val = clause.split(op, 1)
            col, val = col.strip(), val.strip()
            if col == "xsubstr":
                text_cols = [c for c in df.columns if df[c].dtype == object]
                mask = False
                for c in text_cols:
                    mask = mask | df[c].astype(str).str.contains(val, case=False, na=False)
                return df[mask]
            if col == "age":
                val = int(val)
            return df[OPS[op](df[col], val)]
    sys.exit(f"unparseable clause: {clause!r}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--filter", required=True, help='e.g. "age>=25,age<=45,province=서울"')
    ap.add_argument("--n", type=int, required=True, help="number of personas to draw")
    ap.add_argument("--seed", type=int, default=42, help="random_state for reproducibility")
    ap.add_argument("--out", required=True, help="output JSONL path (drawn_personas.jsonl)")
    ap.add_argument("--fields", help="comma-separated column override (default: demographics+persona)")
    args = ap.parse_args()

    cols = [c.strip() for c in args.fields.split(",")] if args.fields else DEFAULT_COLS

    from datasets import load_dataset
    ds = load_dataset(REPO, split="train").select_columns(cols)  # shrink before to_pandas
    df = ds.to_pandas()

    hits = df
    for clause in (c for c in args.filter.split(",") if c.strip()):
        hits = apply_clause(hits, clause.strip())
    print(f"filter {args.filter!r} -> {len(hits):,} rows in population", file=sys.stderr)
    if len(hits) < args.n:
        sys.exit(f"only {len(hits)} rows match; cannot draw n={args.n}. Loosen the filter.")

    sample = hits.sample(n=args.n, random_state=args.seed)
    with open(args.out, "w") as f:
        for _, row in sample.iterrows():
            f.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")
    print(f"wrote {args.n} personas -> {args.out}", file=sys.stderr)
    for _, r in sample.iterrows():                # echo the spine so the caller can verify
        print(f"{r['uuid']}  {r['age']}세 {r['sex']} {r.get('district','')} {r.get('occupation','')}")


if __name__ == "__main__":
    main()
