# Alpaca Paper Runner: trading research team

Paper trading only. Two parts:
1. **Live paper bots** (GitHub Actions + cron-job.org): `runner/` trades BTC/USD (breakout_trend). A stock bot comes later.
2. **Research team** (Agent HQ): finds, tests and reviews strategy ideas. Agents NEVER place orders and NEVER change the live bots.

Idan is learning quant trading by watching this team work. Write for him: plain English, short, numbers with units,
no jargon without a one-line explanation.

## Hard rules (also enforced in .claude/settings.json)
- Never edit `runner/`, `.github/`, `state/`, `.env`, and never `git push`. Pushing changes what the live bot runs.
  Anything that should change a live bot goes to NEEDS-YOU.md as `APPROVE: [BLOCKING] ...` for Idan.
- Never read or print API keys. Never put secrets in any file.
- Rules before results: a hypothesis card's Rules and Variants are committed BEFORE its first backtest. After
  that they are frozen. A changed rule is a new card.
- The holdout (2024-01-01 onward for stocks) stays sealed. Only an `APPROVE: [BLOCKING] run holdout for H###`
  answered APPROVED by Idan allows `allow_holdout=True`, once per card.
- At most 4 variants per card. The more cards we test, the more will pass by luck: the Skeptic says so.
- Every claim cites a file, a number or a link that was actually opened.

## Card lifecycle (research/cards/H###-short-name.md, from research/cards/TEMPLATE.md)
DRAFT (Researcher) -> FROZEN (Quant commits code + card before running) -> TESTED (Quant adds results)
-> REVIEWED (Skeptic verdict: PASS / FAIL / NEEDS WORK) -> [holdout, Idan approves] -> PAPER CANDIDATE.
`research/cards/INDEX.md` lists every card with status and one-line result. Check it before proposing anything.

## Thought log (Idan reads this)
Every agent, every task, appends to `research/journal/YYYY-MM-DD.md`:
```
## HH:MM <agent>: <task title>
**Asked:** ...  **Looked at:** files/links  **Thinking:** the reasoning in 3-8 lines, including doubts
**Did:** ...  **Result:** numbers  **Next / open questions:** ...
```

## Shell rules (Windows; breaking these gets commands refused)
- The shell ALREADY starts in this project folder. Never start a command with `cd`. Never use absolute X:/ paths.
- Read files with the Read / Glob / Grep tools, never `cat`, `ls`, `head`, `tail`, `echo >>` in Bash.
- Edit files with Edit / Write, never shell redirection.
- Bash is only for these, one command per call, no `&&` chains:
  `py -m pytest -q` | `py -m stocks.research --card H###` | `py -m stocks.research` | `git status` | `git diff ...` |
  `git log ...` | `git add <files>` | `git commit -m "..."`
- If a command is refused, do not retry variations. Note the exact error in the journal, put a TRY IT item in
  NEEDS-YOU.md ("tell Claude in the setup chat: <error>"), and do other useful work.

## Commands (Windows, run from this folder)
- Tests: `py -m pytest -q`  (must pass before and after any code change)
- Stock card backtest: `py -m stocks.research --card H003`  -> research/results/H003.md
- Data: 100 stocks, 5-minute bars 2016-04 to 2026-10-27, in stocks/cache (built by `py -m stocks.data`).
  Engine: stocks/engine.py. Strategies + CARDS registry: stocks/strategies.py. Rules: stocks/PROTOCOL.md.
- If numpy or pytest is missing: NEEDS-YOU `TRY IT: run py -m pip install numpy pytest requests`.

## Agent HQ (when a run is started from Agent HQ)
- You are running headless: nobody can answer questions mid-run. Never ask; decide sensibly or put a DECIDE item in NEEDS-YOU.md and stop.
- Agent HQ updates status/*.json itself. Agents skip status-file edits under HQ.
- Planning runs write ONLY .hq/plan.json. Task runs use exactly ONE specialist, never parallel, never background.
- Idan's decisions from the HQ page land in NEEDS-YOU.md "Done" (APPROVED / CHANGES REQUESTED / REJECTED with his note) and in .hq/decisions.jsonl. Read them before planning; a CHANGES note is the next thing to do.
- Anything only Idan can do goes in NEEDS-YOU.md in the usual format. HQ pauses the session until he decides.
- Goal mode: plan small steps; skip work that depends on an unanswered DECIDE/TRY IT and do something else useful meanwhile.
- Only APPROVE items (and any item containing [BLOCKING]) pause goal mode. Add [BLOCKING] to anything touching live bots, money, keys or the holdout.
- Declare the goal done only when its "done when" is met and tested; HQ then asks Idan to confirm.
- Saving usage: read STATE.md first, only the last ~15 lines of LOG.md, and only the files the task needs. Update STATE.md at the end of every task (max 25 lines).
