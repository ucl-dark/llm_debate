#!/usr/bin/env python3
"""quote_budget_rejudge.py — Re-judge each candidate in a saved budget pool M
times to recover its TRUE P(judge picks correct), and test whether best-of-N's
selection criterion (a single judge sample) tracks genuine convincingness or
just noise.

Key comparison: candidates the original single judge call scored > 0 (judge
agreed with the consultant's chosen answer) vs scored 0. If both groups
re-judge to similar P(correct), the original pick was noise and BoN is
selecting luck; if the score>0 group re-judges much higher, BoN selects
genuinely-more-convincing arguments.
"""

import argparse
import asyncio
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.utils import setup_environment
import scripts.quote_budget_3way as q3
from scripts.quote_budget_3way import (cited_sentences, options_for_ordering,
                                       judge_quotes, role_order)


async def rejudge(passage, question, ordering, shown, m):
    options, _ = options_for_ordering(passage, ordering)
    correct_letter = ordering["correct"]
    picks = await asyncio.gather(*[judge_quotes(question, options, shown) for _ in range(m)])
    p_correct = sum(1 for L, _ in picks if L == correct_letter) / m
    return p_correct


async def run(args):
    setup_environment()
    q3.JUDGE_MODEL = args.judge_model
    passage = json.loads(Path(args.passage).read_text())[0]
    cache = json.loads(Path(args.cache).read_text())
    recs, cands = cache["records"], cache["candidates"]
    budget = None if args.budget.lower() in ("inf", "none") else int(args.budget)
    sentences, question = passage["sentences"], passage["question"]
    roles = role_order(passage)

    jobs = []
    for c, r in zip(cands, recs):
        cited = cited_sentences(c, sentences)
        shown = [t for _, t in (cited if budget is None else cited[:budget])]
        ordering = {roles[i]: r["ordering"][i] for i in range(len(roles))}
        jobs.append((r, shown, ordering))

    print(f"re-judging {len(jobs)} candidates x {args.m} (judge={q3.JUDGE_MODEL}, budget={args.budget})\n")
    pcs = await asyncio.gather(*[rejudge(passage, question, o, s, args.m) for (_, s, o) in jobs])

    print(f"  {'orig_pick':>9} {'orig_conf':>9} {'score':>6} {'re-judged P(correct)':>20}")
    for (r, shown, o), pc in zip(jobs, pcs):
        print(f"  {r['judge_role']:>9} {r['confidence']:>9} {r['score']:>6.0f} {pc:>19.2f}")

    won = [pc for (r, _, _), pc in zip(jobs, pcs) if r["score"] > 0]   # judge originally agreed (BoN surfaces these)
    lost = [pc for (r, _, _), pc in zip(jobs, pcs) if r["score"] == 0]
    print("\n  ── summary ──")
    print(f"  pool mean re-judged P(correct):        {statistics.mean(pcs):.2f}")
    if won:
        print(f"  candidates BoN surfaces (orig score>0): {statistics.mean(won):.2f}  (n={len(won)})")
    if lost:
        print(f"  candidates BoN discards (orig score=0): {statistics.mean(lost):.2f}  (n={len(lost)})")
    print("\n  If 'surfaces' >> 'discards', BoN selects genuinely more convincing args.")
    print("  If they're similar, the BoN gain is a single-judge-sample artifact.")
    for model, u in q3.USAGE.items():
        print(f"    {model}: {u['calls']} calls")


def main():
    ap = argparse.ArgumentParser(description="Re-judge a budget pool to test BoN: quality vs noise")
    ap.add_argument("--cache", default="exp/quote_budget_3way_gpt54_flat_fixed/cache/qbudget_3way_4_b1.json")
    ap.add_argument("--passage", default="data/quote_budget/vanishing_manuscript.json")
    ap.add_argument("--budget", default="1")
    ap.add_argument("--judge-model", default="gpt-5.4")
    ap.add_argument("--m", type=int, default=8, help="Re-judges per candidate")
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
