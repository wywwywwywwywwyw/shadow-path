"""Chapter I: search for a lantern/shadow puzzle on a 7x7 courtyard and verify it is solvable.

Rules mirrored from the game:
- the lantern (the orb) hangs at radius R from the post and stops at 8 angles (k * 45 deg)
- a floor tile is walkable when at least 3 of its 5 sample points cannot see the lantern
- the lantern may only sweep through angles that keep the traveller's tile in shadow

Usage:
  python shadow_design.py <seed>    search for new layouts (R and H are set to the game's 1.45 / 2.1)
  python shadow_design.py verify    re-check the shipped chapter I layout (LEVEL) at fine resolution
"""
import math, random, sys
from collections import deque

N = 7
POST = (3, 3)
R, H = 0.95, 2.3
GATE_IN = (1, 0)          # floor tile in front of the moon gate
SAMPLES = 9               # samples per 45 deg sweep


def lamp(theta):
    return (POST[0] + R * math.cos(theta), H, POST[1] + R * math.sin(theta))


def seg_hits_box(p, q, lo, hi):
    t0, t1 = 0.0, 1.0
    for a in range(3):
        d = q[a] - p[a]
        if abs(d) < 1e-9:
            if p[a] < lo[a] or p[a] > hi[a]:
                return False
            continue
        ta, tb = (lo[a] - p[a]) / d, (hi[a] - p[a]) / d
        if ta > tb:
            ta, tb = tb, ta
        t0, t1 = max(t0, ta), min(t1, tb)
        if t0 > t1:
            return False
    return True


def boxes_of(obs):
    out = []
    for o in obs:
        if o[0] == 'pillar':
            _, x, z, h = o
            out.append(((x - 0.35, 0, z - 0.35), (x + 0.35, h, z + 0.35)))
        else:  # wall: ('wall', x, z, length, axis, h) occupying tiles from (x,z) along axis
            _, x, z, ln, axis, h = o
            if axis == 'x':
                out.append(((x - 0.5, 0, z - 0.18), (x + ln - 0.5, h, z + 0.18)))
            else:
                out.append(((x - 0.18, 0, z - 0.5), (x + 0.18, h, z + ln - 0.5)))
    return out


def blocked_tiles(obs):
    b = {POST}
    for o in obs:
        if o[0] == 'pillar':
            b.add((o[1], o[2]))
        else:
            _, x, z, ln, axis, h = o
            for i in range(ln):
                b.add((x + i, z) if axis == 'x' else (x, z + i))
    return b


def point_dark(x, z, q, boxes):
    p = (x, 0.05, z)
    return any(seg_hits_box(p, q, lo, hi) for lo, hi in boxes)


OFFS = ((0, 0), (0.25, 0.25), (-0.25, 0.25), (0.25, -0.25), (-0.25, -0.25))


def shadow_at(tile, theta, boxes):
    """A tile counts as shadow when at least 3 of 5 sample points are dark."""
    q = lamp(theta)
    return sum(point_dark(tile[0] + dx, tile[1] + dz, q, boxes) for dx, dz in OFFS) >= 3


def analyse(obs, start, k0, verbose=False):
    boxes = boxes_of(obs)
    blocked = blocked_tiles(obs)
    tiles = [(x, z) for x in range(N) for z in range(N) if (x, z) not in blocked]
    if start in blocked or GATE_IN in blocked:
        return None
    shade = {k: {t for t in tiles if shadow_at(t, k * math.pi / 4, boxes)} for k in range(8)}

    def sweep_ok(t, k, step):
        a = k * math.pi / 4
        for i in range(1, SAMPLES + 1):
            if not shadow_at(t, a + step * (math.pi / 4) * i / SAMPLES, boxes):
                return False
        return True

    def comp(t, k):
        seen, q = {t}, deque([t])
        while q:
            c = q.popleft()
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + d[0], c[1] + d[1])
                if n in shade[k] and n not in seen:
                    seen.add(n); q.append(n)
        return seen

    if start not in shade[k0]:
        return None
    # states: (tile, k); cost = number of 45deg steps
    dist = {(start, k0): 0}
    prev = {}
    dq = deque([(start, k0)])
    goal = None
    while dq:
        t, k = dq.popleft()
        reach = comp(t, k)
        if GATE_IN in reach:
            goal = (t, k)
            break
        for r in reach:
            for step in (1, -1):
                nk = (k + step) % 8
                if sweep_ok(r, k, step):
                    s = (r, nk)
                    if s not in dist:
                        dist[s] = dist[(t, k)] + 1
                        prev[s] = (t, k)
                        dq.append(s)
    if goal is None:
        return None
    path = [goal]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    return {'rot': dist[goal], 'path': path, 'shade': shade, 'tiles': tiles, 'blocked': blocked}


def draw(obs, res, start, marks=()):
    for k in sorted(set(k for _, k in res['path'])):
        print(f'--- lantern k={k} ({k*45} deg)')
        for z in range(-1, N):
            row = ''
            for x in range(-1, N):
                t = (x, z)
                if t == (1, -1): row += 'G'
                elif z == -1 or x == -1: row += '#'
                elif t == POST: row += 'L'
                elif t in res['blocked']: row += 'X'
                elif t == start: row += 'S' if t in res['shade'][k] else 's'
                elif t in res['shade'][k]: row += ':'
                else: row += '.'
            print(row)


TALL = 2.7


def hidden_by(t, obs):
    """Tiles diagonally behind a tall pillar are hard to see in the isometric view."""
    for o in obs:
        if o[0] == 'pillar' and o[3] >= TALL:
            for k in (1, 2):
                if (t[0] + k, t[1] + k) == (o[1], o[2]):
                    return True
    return False


def random_level(rng):
    obs = []
    used = {POST, GATE_IN}
    for _ in range(rng.choice([2, 3, 3, 4])):
        for _ in range(100):
            t = (rng.randrange(N), rng.randrange(N))
            tall = rng.random() < 0.5
            far = math.hypot(t[0] - POST[0], t[1] - POST[1]) > R + 0.9
            if t not in used and (far or not tall):
                break
        else:
            continue
        used.add(t)
        obs.append(('pillar', t[0], t[1], TALL if tall else 1.2))
    for _ in range(rng.choice([1, 1, 2])):
        for _ in range(60):
            axis = rng.choice('xz')
            ln = rng.choice([2, 3])
            x, z = rng.randrange(N - ln + 1), rng.randrange(N - ln + 1)
            cells = [(x + i, z) if axis == 'x' else (x, z + i) for i in range(ln)]
            if not any(c in used for c in cells):
                used.update(cells)
                obs.append(('wall', x, z, ln, axis, 1.0))
                break
    return obs


def walk_len(res):
    total = 0
    path = res['path'] + [(GATE_IN, res['path'][-1][1])]
    for (a, k), (b, _) in zip(path, path[1:]):
        if a == b: continue
        seen, q = {a: 0}, deque([a])
        while q:
            c = q.popleft()
            if c == b: break
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + d[0], c[1] + d[1])
                if n in res['shade'][k] and n not in seen:
                    seen[n] = seen[c] + 1; q.append(n)
        total += seen.get(b, 99)
    return total


LEVEL = [('pillar', 3, 0, 2.7), ('pillar', 3, 4, 1.2), ('pillar', 1, 5, 2.7),
         ('wall', 2, 1, 3, 'z', 1.0), ('wall', 4, 2, 3, 'z', 1.0)]


def verify():
    global SAMPLES
    SAMPLES = 90
    res = analyse(LEVEL, (6, 6), 5)
    print('fine-sampled solution:', res and res['path'], 'rot', res and res['rot'])
    boxes = boxes_of(LEVEL)
    for k in sorted(set(k for _, k in res['path'])):
        amb = []
        for t in res['tiles']:
            vals = {shadow_at((t[0] + dx, t[1] + dz), k * math.pi / 4, boxes)
                    for dx, dz in ((0, 0), (0.18, 0), (-0.18, 0), (0, 0.18), (0, -0.18))}
            if len(vals) > 1:
                amb.append(t)
        print(f'k={k} edge tiles:', amb)
    draw(LEVEL, res, (6, 6))


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'verify':
    R, H = 1.45, 2.1
    verify()
    sys.exit()

if __name__ == '__main__':
    R, H = 1.45, 2.1
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
    best = []
    for it in range(5000):
        obs = random_level(rng)
        k0 = rng.randrange(8)
        for start in [(6, 6), (5, 6), (6, 5)]:
            res = analyse(obs, start, k0)
            if not res: continue
            stops = len({t for t, _ in res['path']})
            area = sum(len(res['shade'][k]) for _, k in res['path']) / len(res['path']) / len(res['tiles'])
            wl = walk_len(res)
            vis = not any(hidden_by(t, obs) for t, _ in res['path'])
            if 3 <= res['rot'] <= 5 and stops >= 3 and 0.25 <= area <= 0.55 and vis and wl >= 10:
                best.append((stops * 2 + wl * 0.5 - abs(res['rot'] - 4), obs, start, k0, res, area, wl))
    best.sort(key=lambda b: -b[0])
    print('candidates:', len(best))
    for score, obs, start, k0, res, area, wl in best[:4]:
        print('=' * 30, f'score {score:.1f} rot {res["rot"]} k0 {k0} start {start} area {area:.2f} walk {wl}')
        print(obs)
        print('path', res['path'])
        draw(obs, res, start)
