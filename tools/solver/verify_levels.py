"""Re-check the shipped chapters against the rules the game uses.

The chapters are read straight from the JSON block in index.html (see levels.py), so there is
nothing to mirror by hand. Run it after any change to that block:
  python tools/solver/verify_levels.py
Exit code 0 = every check passed.

Every check uses the game's own rule (a tile is shadow when >= 3 of 5 sample points
cannot see the orb) and a fine sweep while a mechanism moves.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import levels               # noqa: E402  reads index.html
import shadow_design as sd  # noqa: E402  orb only
import level2               # noqa: E402  orb + sliding tower
import level3               # noqa: E402  orb + lift pillar

FINE = 45
results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(('PASS  ' if ok else 'FAIL  ') + name + (f'  ({detail})' if detail else ''))


H = levels.lamp_height()
sd.H = level2.H = level3.H = H

for lv in levels.load():
    tag = lv['roman'].ljust(3) + ' '
    post, R, gate_x = levels.post(lv), lv['armR'], lv['gateX']
    start, k0 = levels.tile(lv['start']), lv['startK']

    if lv['slider'] and lv['lift']:
        sys.exit(f"chapter {lv['roman']}: no solver handles a tower and a lift together yet")

    if lv['slider']:
        s = lv['slider']
        lv2 = level2.Level(post, R, levels.pillars(lv), levels.walls(lv),
                           (s['x'], s['z'], s['axis'], s['n'], s['h']), gate_x, start, k0, s['start'])
        r = lv2.solve(full=True, samples=FINE)
        check(tag + 'solvable', r is not None, r and f'{r[0]} moves')
        check(tag + 'needs the tower', lv2.solve(full=True, samples=FINE, allow_slide=False) is None)
        check(tag + 'needs the orb', lv2.solve(full=True, samples=FINE, allow_rot=False) is None)

    elif lv['lift']:
        lift = lv['lift']
        level3.LIFT = [float(h) for h in lift['heights']]
        args = (post, R, levels.pillars(lv), levels.walls(lv), (lift['x'], lift['z']), gate_x, start, k0)
        lv3 = level3.Level(*args, lift['start'])
        r = lv3.solve(full=True, samples=FINE)
        check(tag + 'solvable', r is not None, r and f'{r[0]} moves')
        check(tag + 'needs the lift', lv3.solve(full=True, samples=FINE, allow_lift=False) is None)
        check(tag + 'needs the orb', lv3.solve(full=True, samples=FINE, allow_rot=False) is None)
        check(tag + 'only lowering fails ("drag it to the bottom")', lv3.solve(full=True, samples=FINE, lift_dir=-1) is None)
        check(tag + 'only raising fails', lv3.solve(full=True, samples=FINE, lift_dir=1) is None)
        check(tag + 'must walk over the flush lift', lv3.solve(full=True, samples=FINE, lift_walk=False) is None)
        for h in range(len(level3.LIFT)):
            parked = level3.Level(*args, h).solve(full=True, samples=FINE, allow_lift=False)
            check(tag + f'parking the lift at height {level3.LIFT[h]:.1f} fails', parked is None)

    else:
        sd.R, sd.POST, sd.GATE_IN, sd.SAMPLES = R, post, (gate_x, 0), 90
        res = sd.analyse(levels.obstacles(lv), start, k0)
        check(tag + 'solvable', res is not None, res and f"{res['rot']} turns")
        check(tag + 'needs the orb', bool(res) and res['rot'] > 0)

print(f'\n{sum(results)}/{len(results)} checks passed')
sys.exit(0 if all(results) else 1)
