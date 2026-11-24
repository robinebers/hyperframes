# Carry cost of the frame-source hook (ROB-711, AMCL-395 Q7)

Measures, by running git, what it costs to carry the `spike/host-media` patch on top of upstream HyperFrames.
No numbers here are estimated; every row comes from a merge the scripts ran.

## One command for a new head

```bash
cd <hyperframes checkout>                       # needs remotes origin (fork) and upstream (heygen-com)
git remote add upstream https://github.com/heygen-com/hyperframes.git   # once
GIT_LFS_SKIP_SMUDGE=1 git fetch --filter=blob:none --shallow-since=2026-10-20 upstream main
GIT_LFS_SKIP_SMUDGE=1 git fetch --filter=blob:none upstream 'refs/tags/v0.9.*:refs/tags/v0.9.*'
git worktree add --detach /workspace/wt-check efef865 && (cd /workspace/wt-check && bun install)
git config rerere.enabled false
DROP_FOR_PR=<sha of the audio-clock commit> carry-measure/rerun.sh origin/spike/host-media final
```

`rerun.sh <head> <name>`:
1. walks the new head back to 30 Oct (upstream 443ded42) through the 83 stored versions, replaying the
   stored hand resolutions (`res/*.sh`); it stops on a conflict nobody resolved yet (edit
   `versions-<name>/conflicts/NNN/*`, run `extend-save.py versions-<name> NNN`, add the case to a `res/*.sh`, rerun);
2. replays forward to efef865 in modes b, c, a with type-check and tests at every step (`run-all.sh`);
3. rebases the head onto upstream main as it is now and onto pull request #8636's head (and, with `DROP_FOR_PR`,
   onto #8636 without that commit);
4. prints totals (`totals.py`). Output: `results-<name>/mode-{a,b,c}.tsv`, `today.tsv`, `totals.tsv`.
Mode a takes about an hour on a 2-CPU machine (83 steps, each with a type-check and five test files).

## Files

| file | what |
|---|---|
| walkback.sh, walk-continue.sh | step 1: carry the patch backwards over every touching commit, stop at each conflict |
| resolve.py, strip-ours.py | replace conflict blocks with a given text / keep upstream's side |
| measure.py | one merge: clean or conflict, files, hunks, lines from "ours-stripped" to the resolved tree |
| carry.py | forward replay: `carry.py <patch-commit> <to> <a|b|c> [--tags ..] --versions DIR --check-worktree WT --out TSV` |
| check.sh | core type-check (both tsconfigs) + init.frameSourceMedia, init.buffering, frameSources, media, preloadMedia tests and any test file the patch touches |
| extend.py, extend-all.sh, extend-save.py, res/ | carry a newer head into every stored version, reusing all earlier hand resolutions |
| variant-v1.py | point 5: the one-line variant of the mediaNotReadyAt hunk, derived for every stored version |
| versions/NNN-<upstream>.patch | the patch (head cd9f723) as resolved by hand on each older upstream commit; 000 = efef865, 083 = 443ded42 |
| walkback.tsv, walk-measure.tsv, walk-notes.md, walkback-sites.txt | the walk-back record |
| results/ | forward replay of head cd9f723 (mode-a, mode-b = weeks from 27 Oct, mode-b-mondays, mode-c, variant-v1-mode-a) |
| results-4d15018-smoke/ | smoke run of rerun.sh on head 4d15018, mode b and today only |

## How a step is counted

- "lines": `git diff --numstat` between the mechanical merge with every conflict reduced to upstream's side and
  the hand-resolved tree; test files counted apart as test upkeep.
- "clean_but_differs": git merged without a conflict but the stored resolution differs, because upstream added a
  media call site the patch has to guard. Type-check and tests passed on the mechanical result in all three cases,
  so neither git nor the checks catch it.
- "silent_break": clean merge whose mechanical result fails the type-check or the tests.
