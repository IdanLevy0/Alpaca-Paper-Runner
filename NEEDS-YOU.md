# Needs you (Idan)
Items: `- [ ] TRY IT / DECIDE / APPROVE: ...`. [BLOCKING] items pause the team until you answer in Agent HQ.

## Open

## Done
- [x] DECIDE: Freeze and test H004 (gap-and-go, now drafted) did not run: Bash was denied (it is needed for pytest, git commit and `py -m stocks.research --card H004`). Nothing was changed. Please allow Bash for the quant in Agent HQ (pytest, git add/commit, py -m stocks.research), then re-run the H004 task. H005 follows after H004. -> APPROVED via HQ 2026-11-06
- [x] DECIDE: Task t3 (freeze and test H005) did not run. The quant subagent was denied Bash again (needed for pytest, git commit, the backtest), so nothing was changed. Also, INDEX/STATE list only H001 and H002, so H005 may not exist yet. Please allow Bash for the quant in Agent HQ (pytest, git add/commit, `py -m stocks.research`) and have the Researcher draft the missing cards, then re-run t2/t3. -> APPROVED via HQ 2026-11-06
- [x] DECIDE: Task t2 (freeze and test H004) could not run: there is no H004 card (only H001, H002). Should the Researcher draft it first, or is H004 a different card number? Also the quant subagent was denied Bash (pytest, git commit); check its permissions in Agent HQ before the next quant task. -> APPROVED via HQ 2026-11-06
