"""Re-check the three shipped chapters against the rules the game uses.

Run it after any change to LEVELS in index.html (and mirror the change here first):
  python tools/solver/verify_levels.py
Exit code 0 = every check passed.

Every check uses the game's own rule (a tile is shadow when >= 3 of 5 sample points
cannot see the orb) and a fine sweep while a mechanism moves.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shadow_design as sd  # noqa: E402  chapter I: orb only
import level2               # noqa: E402  chapter II: orb + sliding tower
import level3               # noqa: E402  chapter III: orb + lift pillar

FINE = 45
results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(('PASS  ' if ok else 'FAIL  ') + name + (f'  ({detail})' if detail else ''))


# Chapter I — must match LEVELS[0] in index.html
sd.R, sd.H, sd.SAMPLES = 1.45, 2.1, 90
res = sd.analyse(sd.LEVEL, (6, 6), 5)
check('I   solvable', res is not None, res and f"{res['rot']} turns")
check('I   needs the orb', bool(res) and res['rot'] > 0)

# Chapter II — must match LEVELS[1] in index.html
L2 = ((3, 3), 1.45, [(0, 3, 2.7), (1, 4, 1.2)], [(1, 2, 3, 'x', 1.0)], (4, 3, 'z', 4, 1.8), 2, (0, 6), 6, 1)
lv2 = level2.Level(*L2)
r = lv2.solve(full=True, samples=FINE)
check('II  solvable', r is not None, r and f'{r[0]} moves')
check('II  needs the tower', lv2.solve(full=True, samples=FINE, allow_slide=False) is None)
check('II  needs the orb', lv2.solve(full=True, samples=FINE, allow_rot=False) is None)

# Chapter III — must match LEVELS[2] in index.html
L3 = ((3, 3), 1.45, [(4, 5, 1.2)], [(0, 3, 2, 'z', 1.0), (2, 3, 2, 'z', 1.0)], (1, 2), 1, (0, 6), 7, 1)
lv3 = level3.Level(*L3)
r = lv3.solve(full=True, samples=FINE)
check('III solvable', r is not None, r and f'{r[0]} moves')
check('III needs the lift', lv3.solve(full=True, samples=FINE, allow_lift=False) is None)
check('III needs the orb', lv3.solve(full=True, samples=FINE, allow_rot=False) is None)
check('III only lowering fails ("drag it to the bottom")', lv3.solve(full=True, samples=FINE, lift_dir=-1) is None)
check('III only raising fails', lv3.solve(full=True, samples=FINE, lift_dir=1) is None)
check('III must walk over the flush lift', lv3.solve(full=True, samples=FINE, lift_walk=False) is None)
for h in range(3):
    parked = level3.Level(*L3[:-1], h).solve(full=True, samples=FINE, allow_lift=False)
    check(f'III parking the lift at height {level3.LIFT[h]} fails', parked is None)

print(f'\n{sum(results)}/{len(results)} checks passed')
sys.exit(0 if all(results) else 1)
