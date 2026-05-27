#!/usr/bin/env python3
"""Build notebooks/quote_budget_findings.ipynb from the actual prompts + cached
results of the neutral 3-way quote-budget x best-of-N study.

Run:  python scripts/build_quote_budget_notebook.py
"""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.quote_budget_3way import (bon_pick, build_consultant, build_judge,
                                       make_orderings, render_for_ordering, role_order)

RUN = ROOT / "exp/quote_budget_3way_neutral"
PASSAGE = ROOT / "data/quote_budget/vanishing_manuscript_neutral.json"
BUDGETS = ["1", "2", "3", "inf"]
BONS = [1, 2, 4, 8, 16, 24]

# ── pull the real passage + prompts ───────────────────────────────────────────
passage = json.loads(PASSAGE.read_text())[0]
roles = role_order(passage)
ordering = make_orderings(roles, "ABC")[0]           # correct=A, trap=B, third=C
story, sents, options, _ = render_for_ordering(passage, ordering)
consultant_prompt = build_consultant(passage["question"], options, story, 2)[0]["content"]
judge_prompt = build_judge(passage["question"], options,
                           ["Suspect B's building badge recorded them leaving ... at 8:50 p.m. ...",
                            "Suspect C spent the evening ... on a video call ... 8:00 to 9:30 p.m."])[0]["content"]

# ── compute the result grids (for embedded markdown tables) ───────────────────
recs = json.loads((RUN / "details.json").read_text())
groups = defaultdict(list)
for r in recs:
    groups[r["budget_label"]].append(r)
rng = random.Random(0)


def grid(metric):
    return {b: {k: bon_pick(groups[b], k, metric, 800, rng) for k in BONS} for b in BUDGETS}


acc, trap = grid("judge_correct"), grid("chose_trap")


def table_bon_rows(g):
    hdr = "| BoN \\ budget | " + " | ".join(BUDGETS) + " |\n"
    sep = "|" + "---|" * (len(BUDGETS) + 1) + "\n"
    body = "".join(
        "| " + str(k) + " | " + " | ".join(f"{g[b][k]*100:.0f}%" for b in BUDGETS) + " |\n"
        for k in BONS)
    return hdr + sep + body


# ── notebook cells ────────────────────────────────────────────────────────────
md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell
cells = []

cells.append(md(
    "# Quote budget × best-of-N in a no-context consultancy\n"
    "\n"
    "**Question.** When a consultant argues for an answer and a judge that *cannot see the "
    "passage* decides based only on the consultant's quotes, does limiting the number of "
    "quotes (the *budget*) let a misleading argument win — and does **best-of-N** "
    "(letting the consultant submit its most convincing of N attempts) amplify that?\n"))

cells.append(md(
    "## 1. Setup\n"
    "\n"
    "- A **consultant** reads a passage, picks one of **three** answers, and supports it with "
    "**at most N verbatim quotes** (each a single sentence).\n"
    "- A **no-context judge** sees *only* the consultant's quotes (not the passage) plus the three "
    "answer options, and picks one + a confidence.\n"
    "- We sweep the **quote budget** (1, 2, 3, ∞) and the **best-of-N** selection.\n"
    "- The passage is a **3-way elimination mystery**: the **correct** answer is a pure *residue* "
    "(provable only by ruling the others out); one distractor — the **trap** — carries salient but "
    "*misleading* incriminating evidence (a motive); the **third** suspect has an alibi. The correct "
    "answer needs the full elimination, so `K = 2` (both alibis).\n"
    "- **Neutral, counterbalanced labels** (`Suspect A/B/C`, with roles randomly assigned to letters "
    "per trial) remove name/position priors that earlier confounded the judge.\n"
    "- **Best-of-N** = generate N candidate arguments, keep the one the judge is most confident in "
    "(its confidence in the consultant's chosen answer). Computed by resampling from the candidate "
    "pool.\n"))

cells.append(md(
    "## 2. The passage\n"
    "\n"
    "Templated; `{TRAP}/{THIRD}/{CORRECT}` are substituted with `Suspect A/B/C` per trial (here: "
    "correct=A, trap=B, third=C). The judge never sees this — only the quotes the consultant selects.\n"
    "\n> " + story.replace("\n", "\n> ") + "\n"
    "\n"
    "**Roles:** trap (B) = motive `s3`,`s4` + alibi `s6`; third (C) = alibi `s7`; "
    "correct (A) = residue (appears only in the suspect list). `K=2` = the two alibis `s6`+`s7` "
    "needed to corner the residue.\n"))

cells.append(md("## 3. Consultant & judge prompts\n"))
cells.append(md("**Consultant** (gpt-4o-mini), shown at budget = 2:\n\n```\n" + consultant_prompt + "\n```\n"))
cells.append(md("**Judge** (gpt-5.4), pure-quotes — sees only the quotes + options:\n\n```\n" + judge_prompt + "\n```\n"))
cells.append(code(
    "# Reproduce the prompts from the live builders\n"
    "import json, sys\n"
    "from pathlib import Path\n"
    "ROOT = Path.cwd()\n"
    "while not (ROOT/'scripts'/'quote_budget_3way.py').exists() and ROOT != ROOT.parent:\n"
    "    ROOT = ROOT.parent\n"
    "sys.path.insert(0, str(ROOT))\n"
    "from scripts.quote_budget_3way import (build_consultant, build_judge, render_for_ordering,\n"
    "                                       make_orderings, role_order)\n"
    "p = json.loads((ROOT/'data/quote_budget/vanishing_manuscript_neutral.json').read_text())[0]\n"
    "roles = role_order(p); ordering = make_orderings(roles,'ABC')[0]\n"
    "story, sents, options, _ = render_for_ordering(p, ordering)\n"
    "print(build_consultant(p['question'], options, story, 2)[0]['content'])\n"))

cells.append(md(
    "## 4. Trials & models\n"
    "\n"
    "| | |\n|---|---|\n"
    "| Consultant | **gpt-4o-mini**, temperature **1.2** (high, to spread its choices) |\n"
    "| Judge | **gpt-5.4**, temperature **0**, *pure-quotes* (passage hidden) |\n"
    "| Side classifier | gpt-4o-mini (labels which answer each argument advocates) |\n"
    "| Candidates / budget | **48**, each with a random role→letter ordering (6 perms, counterbalanced) |\n"
    "| Quote budgets | **1, 2, 3, ∞** (∞ = no cap); `K = 2` |\n"
    "| Best-of-N | resampled from the 48-pool; N ∈ {1, 2, 4, 8, 16, 24} |\n"
    "| Budget enforcement | by **passage sentences** (multi-sentence quotes are split & capped), not `<quote>` tags |\n"
    "\n"
    "Passage: `data/quote_budget/vanishing_manuscript_neutral.json`. "
    "Run output: `exp/quote_budget_3way_neutral/`. Script: `scripts/quote_budget_3way.py`.\n"
    "\n"
    "*Caveats:* gpt-4o-mini often fails to identify the residue under neutral labels (raw correct-rate "
    "≈25–37%); the gpt-5.4 judge weighs *motive > alibi* even when both are shown; with only 48 "
    "candidates the N≥16 points are noisy.\n"))

cells.append(code(
    "# Load cached results and build the budget x best-of-N grids (no API calls)\n"
    "import json, random, sys\n"
    "from pathlib import Path\n"
    "from collections import defaultdict\n"
    "import pandas as pd\n"
    "ROOT = Path.cwd()\n"
    "while not (ROOT/'scripts'/'quote_budget_3way.py').exists() and ROOT != ROOT.parent:\n"
    "    ROOT = ROOT.parent\n"
    "sys.path.insert(0, str(ROOT))\n"
    "from scripts.quote_budget_3way import bon_pick\n"
    "recs = json.loads((ROOT/'exp/quote_budget_3way_neutral/details.json').read_text())\n"
    "groups = defaultdict(list)\n"
    "for r in recs: groups[r['budget_label']].append(r)\n"
    "BUDGETS = ['1','2','3','inf']; BONS = [1,2,4,8,16,24]\n"
    "rng = random.Random(0)\n"
    "def grid(metric):\n"
    "    return {b: {k: bon_pick(groups[b], k, metric, 800, rng) for k in BONS} for b in BUDGETS}\n"
    "acc, trap, qgen = grid('judge_correct'), grid('chose_trap'), grid('n_tags')\n"
    "def df(g): return (pd.DataFrame(g).reindex(BONS) * (100 if g is not qgen else 1)).round(0).astype(int)\n"
    "print('Judge accuracy (%) — rows=BoN, cols=budget'); display(df(acc))\n"
    "print('Trap rate (%) — rows=BoN, cols=budget'); display(df(trap))\n"))

cells.append(md(
    "## 5a. Effect of best-of-N, within each budget\n"
    "\n"
    "**Judge accuracy** (rows = best-of-N, cols = budget):\n\n" + table_bon_rows(acc) + "\n"
    "**Trap rate** (rows = best-of-N, cols = budget):\n\n" + table_bon_rows(trap) + "\n"
    "**The sign of best-of-N flips with the budget:**\n"
    "- At **budget 2 (= K) and ∞**, more retries → **truth** (accuracy → ~100%, trap → 0). When the "
    "budget is enough to show the full exoneration, best-of-N surfaces the genuinely-correct "
    "elimination argument.\n"
    "- At **budget 1** (and, messily, **budget 3**), more retries → **the trap** (trap rate climbs, "
    "accuracy stalls/falls). When you can show salient bad evidence but not force the exoneration, "
    "best-of-N surfaces the most-convincing *misleading* argument.\n"))

cells.append(md(
    "## 5b. Effect of the quote budget, at each best-of-N\n"
    "\n"
    "Reading the same tables *across* budgets:\n"
    "- **Accuracy is non-monotonic in budget — a valley at budget 3** (the *obfuscation zone*: room "
    "to show the misleading motive without being forced to reveal the alibis), with peaks at budget "
    "2 and ∞. Going **2 → 3 actually hurts**; **3 → ∞ helps**.\n"
    "- **The budget effect grows with N:** at BoN=1 accuracy spans only ~19–53% across budgets; by "
    "BoN=24 it spans ~53–100%. Best-of-N magnifies the gap between truth-favoring budgets (2, ∞) and "
    "obfuscation-prone ones (1, 3).\n"
    "- **Trap rate peaks at budget 3** (max ≈57% at BoN=8); budget 1's trap rate climbs with N; "
    "budgets 2 and ∞ stay low and fall to 0.\n"
    "\n"
    "*Why:* the trap's **motive** quotes are the only incriminating evidence in the passage — whoever "
    "quotes them steers the judge to the trap; the correct (residue) answer is reachable only by "
    "showing the **full** elimination. At mid-budget you can show the misleading motive but omit the "
    "exoneration → trap wins; at full budget the alibis get shown → truth wins.\n"
    "\n"
    "*Aside:* at **∞** the consultant **self-limits to ~2 quotes** (it does not exploit the unlimited "
    "budget), so ∞ behaves like a ~2-quote regime by the model's own choice.\n"))

cells.append(code(
    "# Plots: best-of-N curves per budget, and budget curves per best-of-N\n"
    "%matplotlib inline\n"
    "import matplotlib.pyplot as plt\n"
    "xb = {'1':1,'2':2,'3':3,'inf':4}\n"
    "fig, ax = plt.subplots(2, 2, figsize=(13, 9))\n"
    "for b in BUDGETS:\n"
    "    ax[0,0].plot(BONS, [acc[b][k]*100 for k in BONS], marker='o', label=f'budget {b}')\n"
    "    ax[0,1].plot(BONS, [trap[b][k]*100 for k in BONS], marker='o', label=f'budget {b}')\n"
    "for a,(g,t) in zip(ax[0], [(acc,'judge accuracy (%)'),(trap,'trap rate (%)')]):\n"
    "    a.set_xscale('log', base=2); a.set_xlabel('best-of-N'); a.set_ylabel(t)\n"
    "    a.set_title(t.split(' (')[0]+' vs best-of-N'); a.legend(); a.grid(alpha=.3)\n"
    "for k in [1,4,8,24]:\n"
    "    ax[1,0].plot([xb[b] for b in BUDGETS], [acc[b][k]*100 for b in BUDGETS], marker='o', label=f'N={k}')\n"
    "    ax[1,1].plot([xb[b] for b in BUDGETS], [trap[b][k]*100 for b in BUDGETS], marker='o', label=f'N={k}')\n"
    "for a,t in zip(ax[1], ['judge accuracy (%)','trap rate (%)']):\n"
    "    a.set_xticks(list(xb.values())); a.set_xticklabels(BUDGETS); a.set_xlabel('quote budget')\n"
    "    a.set_ylabel(t); a.set_title(t.split(' (')[0]+' vs budget'); a.legend(); a.grid(alpha=.3)\n"
    "plt.tight_layout(); plt.show()\n"))

cells.append(md(
    "## Takeaways\n"
    "\n"
    "1. **Best-of-N is double-edged: its sign depends on the budget.** It drives accuracy toward "
    "~100% at budgets 2 and ∞, but toward the trap at budgets 1 and 3.\n"
    "2. **More quotes is not uniformly better.** Accuracy has an obfuscation valley at budget 3; "
    "budget 2 (= K, exactly enough to show the clean elimination) and ∞ are the safe budgets.\n"
    "3. **The mechanism is selective evidence.** The trap's motive is the only incriminating "
    "material; a budget that lets you show it while hiding the exoneration is where best-of-N "
    "manufactures convincing-but-wrong answers.\n"))

nb = nbf.v4.new_notebook(cells=cells, metadata={"language_info": {"name": "python"}})
out = ROOT / "notebooks/quote_budget_findings.ipynb"
out.write_text(nbf.writes(nb))
print(f"wrote {out}")
