"""Search for a level-3 puzzle: the rotating orb plus a lift pillar with three heights.

- lift heights: 0 (flush with the floor, walkable when in shadow), 1.2, 2.6
- the lift cannot rise while the traveller stands on it
- changing height, like turning the orb, must keep her tile in shadow the whole way
- tile walkable when >= 3 of 5 samples are dark (screening uses the centre only)
"""
import math, random, sys
from collections import deque

N = 7
H = 2.1
TALL = 2.7
LIFT = [0.0, 1.2, 2.6]


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


def pbox(x, z, h):
    return ((x - 0.35, 0, z - 0.35), (x + 0.35, h, z + 0.35))


def wbox(x, z, ln, axis, h):
    if axis == 'x':
        return ((x - 0.5, 0, z - 0.18), (x + ln - 0.5, h, z + 0.18))
    return ((x - 0.18, 0, z - 0.5), (x + 0.18, h, z + ln - 0.5))


OFFS_FULL = ((0, 0), (0.25, 0.25), (-0.25, 0.25), (0.25, -0.25), (-0.25, -0.25))


class Level:
    def __init__(self, post, R, pillars, walls, lift, gate_x, start, k0, h0):
        self.post, self.R, self.pillars, self.walls, self.lift = post, R, pillars, walls, lift
        self.gate_x, self.start, self.k0, self.h0 = gate_x, start, k0, h0
        self.static = [pbox(x, z, h) for x, z, h in pillars] + [wbox(*w) for w in walls]
        blocked = {post} | {(x, z) for x, z, _ in pillars}
        for x, z, ln, axis, _ in walls:
            for i in range(ln):
                blocked.add((x + i, z) if axis == 'x' else (x, z + i))
        self.blocked = blocked
        self.tiles = [(x, z) for x in range(N) for z in range(N) if (x, z) not in blocked]
        self.gate_in = (gate_x, 0)
        self.cache = {}

    def lamp(self, theta):
        return (self.post[0] + self.R * math.cos(theta), H, self.post[1] + self.R * math.sin(theta))

    def dark(self, tile, theta, height, full):
        q = self.lamp(theta)
        boxes = self.static + ([pbox(self.lift[0], self.lift[1], height)] if height > 0.01 else [])
        offs = OFFS_FULL if full else ((0, 0),)
        hits = sum(1 for dx, dz in offs
                   if any(seg_hits_box((tile[0] + dx, 0.05, tile[1] + dz), q, lo, hi) for lo, hi in boxes))
        return hits >= (3 if full else 1)

    def shade(self, k, h, full, lift_walk=True):
        key = (k, h, full, lift_walk)
        if key not in self.cache:
            out = set()
            for t in self.tiles:
                if t == self.lift and (LIFT[h] > 0.01 or not lift_walk):
                    continue
                if self.dark(t, k * math.pi / 4, LIFT[h], full):
                    out.add(t)
            self.cache[key] = out
        return self.cache[key]

    def solve(self, full=False, allow_rot=True, allow_lift=True, lift_walk=True, samples=8, lift_dir=0):
        """lift_dir: 0 = free, -1 = may only go down, +1 = may only go up"""
        start = (self.start, self.k0, self.h0)
        if self.start not in self.shade(self.k0, self.h0, full, lift_walk):
            return None

        def comp(t, k, h):
            sh = self.shade(k, h, full, lift_walk)
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
            t, k, h = dq.popleft()
            reach = comp(t, k, h)
            if self.gate_in in reach:
                path = [(t, k, h)]
                while path[-1] in prev:
                    path.append(prev[path[-1]])
                return dist[(t, k, h)], path[::-1]
            for r in reach:
                moves = []
                if allow_rot:
                    for step in (1, -1):
                        if all(self.dark(r, (k + step * i / samples) * math.pi / 4, LIFT[h], full) for i in range(1, samples + 1)):
                            moves.append((r, (k + step) % 8, h))
                if allow_lift:
                    for step in (1, -1):
                        if lift_dir and step != lift_dir:
                            continue
                        nh = h + step
                        if not 0 <= nh < len(LIFT):
                            continue
                        if r == self.lift and nh > 0:
                            continue
                        a, b = LIFT[h], LIFT[nh]
                        if all(self.dark(r, k * math.pi / 4, a + (b - a) * i / samples, full) for i in range(1, samples + 1)):
                            moves.append((r, k, nh))
                for st in moves:
                    if st not in dist:
                        dist[st] = dist[(t, k, h)] + 1
                        prev[st] = (t, k, h)
                        dq.append(st)
        return None


def random_level(rng):
    post = rng.choice([(3, 3), (3, 2), (2, 3), (4, 3), (3, 4)])
    R = rng.choice([1.2, 1.45])
    near = lambda t, m=0.9: math.hypot(t[0] - post[0], t[1] - post[1]) < R + m
    gate_x = rng.choice([1, 3, 4, 5])
    used = {post, (gate_x, 0)}
    lift = None
    for _ in range(60):
        t = (rng.randrange(N), rng.randrange(N))
        if t not in used and not near(t, 0.7):
            lift = t
            used.add(t)
            break
    if not lift:
        return None
    pillars = []
    for _ in range(rng.choice([1, 2, 2, 3])):
        for _ in range(60):
            t = (rng.randrange(N), rng.randrange(N))
            tall = rng.random() < 0.5
            if t not in used and not (tall and near(t)):
                used.add(t)
                pillars.append((t[0], t[1], TALL if tall else 1.2))
                break
    walls = []
    for _ in range(rng.choice([1, 1, 2])):
        for _ in range(60):
            axis, ln = rng.choice('xz'), rng.choice([2, 3])
            x, z = rng.randrange(N - ln + 1), rng.randrange(N - ln + 1)
            cells = [(x + i, z) if axis == 'x' else (x, z + i) for i in range(ln)]
            if not any(c in used for c in cells):
                used.update(cells)
                walls.append((x, z, ln, axis, 1.0))
                break
    return post, R, pillars, walls, lift, gate_x


START_TILES = [(6, 6), (5, 6), (6, 5), (4, 6), (6, 4), (0, 6), (1, 6), (6, 0), (6, 1)]

if __name__ == '__main__':
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
    iters = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
    found = []
    for it in range(iters):
        spec = random_level(rng)
        if not spec:
            continue
        post, R, pillars, walls, lift, gate_x = spec
        for start in START_TILES:
            # the route should travel: start and door far apart
            if abs(start[0] - gate_x) + start[1] < 6:
                continue
            lv = Level(post, R, pillars, walls, lift, gate_x, start, rng.randrange(8), rng.randrange(3))
            if start in lv.blocked or start == lift:
                continue
            res = lv.solve()
            if not res:
                continue
            cost, path = res
            if not (5 <= cost <= 10):
                continue
            if lv.solve(allow_lift=False) or lv.solve(allow_rot=False):
                continue
            # "set it once and forget it" must never be enough: with the lift parked at any
            # single height for the whole level, the door stays out of reach
            if any(Level(post, R, pillars, walls, lift, gate_x, start, lv.k0, h).solve(allow_lift=False) for h in range(3)):
                continue
            # strict: the lift has to change direction at least once
            strict = lv.solve(lift_dir=1) is None and lv.solve(lift_dir=-1) is None
            lifts = sum(1 for a, b in zip(path, path[1:]) if a[2] != b[2])
            rots = cost - lifts
            stops = len({p[0] for p in path})
            # lift "phases": runs of lift moves separated by walking or turning
            phases = sum(1 for i in range(1, len(path)) if path[i][2] != path[i - 1][2]
                         and (i == 1 or path[i - 1][2] == path[i - 2][2] or path[i][0] != path[i - 1][0]))
            walk_over = lv.solve(lift_walk=False) is None   # the flush lift must be walked over
            if rots >= 2 and stops >= 3:
                score = stops + phases * 2 + min(lifts, rots) + (3 if walk_over else 0) + (10 if strict else 0)
                found.append((score, lv, cost, lifts, rots, walk_over, path, strict))
    found.sort(key=lambda f: -f[0])
    print('found', len(found), 'strict', sum(1 for f in found if f[7]))
    for score, lv, cost, lifts, rots, walk_over, path, strict in found[:3]:
        full = lv.solve(full=True, samples=45)
        parked = [bool(Level(lv.post, lv.R, lv.pillars, lv.walls, lv.lift, lv.gate_x, lv.start, lv.k0, h).solve(full=True, allow_lift=False, samples=45)) for h in range(3)]
        print('=' * 20, f'score {score} strict {strict} cost {cost} lifts {lifts} rots {rots} walk_over {walk_over} | full-rule: {full and full[0]} parked-solvable: {parked}')
        print('post', lv.post, 'R', lv.R, 'pillars', lv.pillars, 'walls', lv.walls, 'lift', lv.lift,
              'gate_x', lv.gate_x, 'start', lv.start, 'k0', lv.k0, 'h0', lv.h0)
        print('path', path)
        if full:
            print('full path', full[1])
