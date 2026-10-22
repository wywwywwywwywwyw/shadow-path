"""Search for a level-2 puzzle: one rotating orb plus one tower that slides along a track.

Rules mirrored from the game:
- the orb rests every 45 degrees at radius R around its post, height H
- a tile is walkable when >= 3 of 5 sample points cannot see the orb (screening uses the centre only)
- the orb may only sweep through angles that keep the traveller's tile in shadow
- the slider moves one cell at a time along its track, never onto the traveller,
  and only if her tile stays in shadow for the whole slide
"""
import math, random, sys
from collections import deque

N = 7
H = 2.1
TALL = 2.7


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


def pillar_box(x, z, h, half=0.35):
    return ((x - half, 0, z - half), (x + half, h, z + half))


def wall_box(x, z, ln, axis, h):
    if axis == 'x':
        return ((x - 0.5, 0, z - 0.18), (x + ln - 0.5, h, z + 0.18))
    return ((x - 0.18, 0, z - 0.5), (x + 0.18, h, z + ln - 0.5))


class Level:
    def __init__(self, post, R, pillars, walls, slider, gate_x, start, k0, s0):
        self.post, self.R = post, R
        self.pillars, self.walls, self.slider = pillars, walls, slider
        self.gate_x, self.start, self.k0, self.s0 = gate_x, start, k0, s0
        self.static = [pillar_box(x, z, h) for x, z, h in pillars] + [wall_box(*w) for w in walls]
        blocked = {post} | {(x, z) for x, z, _ in pillars}
        for x, z, ln, axis, _ in walls:
            for i in range(ln):
                blocked.add((x + i, z) if axis == 'x' else (x, z + i))
        self.blocked = blocked
        self.tiles = [(x, z) for x in range(N) for z in range(N) if (x, z) not in blocked]
        self.gate_in = (gate_x, 0)
        self.cache = {}

    def slider_cell(self, s):
        sx, sz, axis, n, h = self.slider
        return (sx + s, sz) if axis == 'x' else (sx, sz + s)

    def slider_box(self, s):
        sx, sz, axis, n, h = self.slider
        if axis == 'x':
            return pillar_box(sx + s, sz, h)
        return pillar_box(sx, sz + s, h)

    def lamp(self, theta):
        return (self.post[0] + self.R * math.cos(theta), H, self.post[1] + self.R * math.sin(theta))

    def dark(self, tile, theta, s, full):
        q = self.lamp(theta)
        boxes = self.static + [self.slider_box(s)]
        offs = ((0, 0), (0.25, 0.25), (-0.25, 0.25), (0.25, -0.25), (-0.25, -0.25)) if full else ((0, 0),)
        hits = 0
        for dx, dz in offs:
            p = (tile[0] + dx, 0.05, tile[1] + dz)
            if any(seg_hits_box(p, q, lo, hi) for lo, hi in boxes):
                hits += 1
        return hits >= (3 if full else 1)

    def shade(self, k, s, full):
        key = (k, s, full)
        if key not in self.cache:
            cell = self.slider_cell(s)
            self.cache[key] = {t for t in self.tiles if t != cell and self.dark(t, k * math.pi / 4, s, full)}
        return self.cache[key]

    def solve(self, full=False, allow_rot=True, allow_slide=True, samples=8):
        sx, sz, axis, n, h = self.slider
        start = (self.start, self.k0, self.s0)
        if self.start not in self.shade(self.k0, self.s0, full):
            return None

        def comp(t, k, s):
            sh = self.shade(k, s, full)
            seen, q = {t}, deque([t])
            while q:
                c = q.popleft()
                for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nb = (c[0] + d[0], c[1] + d[1])
                    if nb in sh and nb not in seen:
                        seen.add(nb); q.append(nb)
            return seen

        dist, prev, dq = {start: 0}, {}, deque([start])
        while dq:
            t, k, s = dq.popleft()
            reach = comp(t, k, s)
            if self.gate_in in reach:
                path = [(t, k, s)]
                while path[-1] in prev:
                    path.append(prev[path[-1]])
                return dist[(t, k, s)], path[::-1]
            for r in reach:
                moves = []
                if allow_rot:
                    for step in (1, -1):
                        ok = all(self.dark(r, (k + step * i / samples) * math.pi / 4, s, full) for i in range(1, samples + 1))
                        if ok:
                            moves.append((r, (k + step) % 8, s))
                if allow_slide:
                    for step in (1, -1):
                        ns = s + step
                        if 0 <= ns < n and self.slider_cell(ns) != r:
                            # interpolate the slider between cells while checking her tile
                            ok = True
                            for i in range(1, samples + 1):
                                f = s + step * i / samples
                                if not self._dark_frac(r, k, f, full):
                                    ok = False
                                    break
                            if ok:
                                moves.append((r, k, ns))
                for st in moves:
                    if st not in dist:
                        dist[st] = dist[(t, k, s)] + 1
                        prev[st] = (t, k, s)
                        dq.append(st)
        return None

    def _dark_frac(self, tile, k, f, full):
        sx, sz, axis, n, h = self.slider
        q = self.lamp(k * math.pi / 4)
        box = pillar_box(sx + f, sz, h) if axis == 'x' else pillar_box(sx, sz + f, h)
        boxes = self.static + [box]
        offs = ((0, 0), (0.25, 0.25), (-0.25, 0.25), (0.25, -0.25), (-0.25, -0.25)) if full else ((0, 0),)
        hits = sum(1 for dx, dz in offs
                   if any(seg_hits_box((tile[0] + dx, 0.05, tile[1] + dz), q, lo, hi) for lo, hi in boxes))
        return hits >= (3 if full else 1)


def random_level(rng):
    post = rng.choice([(3, 3), (3, 2), (2, 3), (4, 3), (3, 4)])
    R = rng.choice([1.2, 1.45])
    used = {post}
    gate_x = rng.choice([1, 2, 4, 5])
    used.add((gate_x, 0))
    near = lambda t: math.hypot(t[0] - post[0], t[1] - post[1]) < R + 0.9
    pillars = []
    for _ in range(rng.choice([1, 2, 2, 3])):
        for _ in range(60):
            t = (rng.randrange(N), rng.randrange(N))
            tall = rng.random() < 0.55
            if t not in used and not (tall and near(t)):
                used.add(t)
                pillars.append((t[0], t[1], TALL if tall else 1.2))
                break
    walls = []
    for _ in range(rng.choice([0, 1, 1, 2])):
        for _ in range(60):
            axis, ln = rng.choice('xz'), rng.choice([2, 3])
            x, z = rng.randrange(N - ln + 1), rng.randrange(N - ln + 1)
            cells = [(x + i, z) if axis == 'x' else (x, z + i) for i in range(ln)]
            if not any(c in used for c in cells):
                used.update(cells)
                walls.append((x, z, ln, axis, 1.0))
                break
    for _ in range(80):
        axis, n = rng.choice('xz'), rng.choice([3, 4])
        x, z = rng.randrange(N - (n - 1 if axis == 'x' else 0)), rng.randrange(N - (n - 1 if axis == 'z' else 0))
        cells = [(x + i, z) if axis == 'x' else (x, z + i) for i in range(n)]
        h = rng.choice([1.4, 1.8, TALL])
        if any(c in used for c in cells):
            continue
        if h > 1.9 and any(near(c) for c in cells):
            continue
        slider = (x, z, axis, n, h)
        used.update(cells)
        break
    else:
        return None
    return post, R, pillars, walls, slider, gate_x


if __name__ == '__main__':
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
    iters = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
    found = []
    for it in range(iters):
        spec = random_level(rng)
        if not spec:
            continue
        post, R, pillars, walls, slider, gate_x = spec
        n = slider[3]
        for start in [(6, 6), (5, 6), (6, 5), (0, 6), (6, 0)]:
            lv = Level(post, R, pillars, walls, slider, gate_x, start, rng.randrange(8), rng.randrange(n))
            if start in lv.blocked or lv.slider_cell(lv.s0) == start:
                continue
            res = lv.solve()
            if not res:
                continue
            cost, path = res
            if not (5 <= cost <= 8):
                continue
            if lv.solve(allow_slide=False) or lv.solve(allow_rot=False):
                continue
            slides = sum(1 for a, b in zip(path, path[1:]) if a[2] != b[2])
            rots = cost - slides
            stops = len({p[0] for p in path})
            if slides >= 2 and rots >= 2 and stops >= 3:
                found.append((stops + min(slides, rots), lv, cost, slides, rots, path))
    found.sort(key=lambda f: -f[0])
    print('found', len(found))
    for score, lv, cost, slides, rots, path in found[:6]:
        full = lv.solve(full=True, samples=45)
        print('=' * 20, f'score {score} cost {cost} slides {slides} rots {rots} | full-rule: {full and full[0]}')
        print('post', lv.post, 'R', lv.R, 'pillars', lv.pillars, 'walls', lv.walls, 'slider', lv.slider,
              'gate_x', lv.gate_x, 'start', lv.start, 'k0', lv.k0, 's0', lv.s0)
        print('path', path)
        if full:
            print('full path', full[1])
