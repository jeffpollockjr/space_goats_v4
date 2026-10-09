# Completed validation

Verified on 2026-10-09 using Python 3.12.14.

- All **55 deterministic tests** passed. The suite covers each Action,
  Goat scoring, all three Block restrictions, the four Specials, recursive
  Nanny draws, setup, hand limits, illegal targets, rule variants, public-only
  AI information, and Final Orbit at normal/start/extra-draw exhaustion.
- Tests also cover exact ties, fractional win credits, original-owner holding
  times, quick/slow/never buckets, card-count reconciliation, CLI errors,
  execution from another directory, and byte-identical event replay.
- Ran **1,000 games for each of 2, 3, 4, and 5 players** with master seed 42
  and `--validate`. This is 4,000 complete games and 416,000 acquisitions.
- Card conservation was checked after every play and completed turn. No
  card was lost, duplicated, or put in an invalid zone.
- Audited the generated CSVs: all player row counts, usage buckets, 100% total
  win credits, balanced starters, and exactly one final turn per player
  reconciled.
- The bundled deck matches the supplied CSV byte for byte.

| Players | Games | Card acquisitions | Avg turns per player | Shared-winner games | Win rates |
| ---: | ---: | ---: | ---: | ---: | --- |
| 2 | 1,000 | 104,000 | 29.37 | 4 | Player 1: 51.30%, Player 2: 48.70% |
| 3 | 1,000 | 104,000 | 20.52 | 25 | Player 1: 35.40%, Player 2: 32.70%, Player 3: 31.90% |
| 4 | 1,000 | 104,000 | 15.58 | 28 | Player 1: 23.35%, Player 2: 24.15%, Player 3: 24.70%, Player 4: 27.80% |
| 5 | 1,000 | 104,000 | 12.42 | 53 | Player 1: 20.20%, Player 2: 18.28%, Player 3: 19.92%, Player 4: 21.78%, Player 5: 19.82% |

These are baseline-AI results using the documented rule assumptions. Win rates
include fractional tie credit; rounded displayed percentages can differ from
100% by a rounding increment. The four-player exports are in `sample_results`.

The test environment was Linux. The runner uses only Python's standard library
and portable paths, with commands supplied for macOS/Linux and Windows. The
same seed is tested for reproducibility on the installed Python runtime;
exact shuffle reproducibility across future Python releases is not promised.

To rerun validation:

```bash
python3 -m unittest discover -s tests -v
python3 run_simulations.py --players 4 --simulations 1000 --seed 42 --validate
```

Original deck SHA-256:
`ab9deebb2118ce96ad1fc734e81283edf5d9b85f52c081a7d3b731faf871cb2a`
