"""Read the shipped chapters straight out of index.html, so the solver checks exactly what the game plays.

The chapters live in one place: the <script type="application/json" id="levels"> block in index.html.
The orb's height comes from `const LAMP_Y = ...;` in the same file.
"""
import json
import os
import re

INDEX = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'index.html')


def _html():
    with open(INDEX, encoding='utf-8') as f:
        return f.read()


def load():
    m = re.search(r'<script type="application/json" id="levels">(.*?)</script>', _html(), re.S)
    if not m:
        raise SystemExit('index.html has no <script type="application/json" id="levels"> block')
    return json.loads(m.group(1))


def lamp_height():
    m = re.search(r'const LAMP_Y = ([\d.]+);', _html())
    if not m:
        raise SystemExit('index.html has no "const LAMP_Y = ...;" line')
    return float(m.group(1))


def tile(s):
    """'x,z' -> (x, z)"""
    x, z = s.split(',')
    return int(x), int(z)


def post(lv):
    return lv['post']['x'], lv['post']['z']


def pillars(lv):
    return [(p['x'], p['z'], p['h']) for p in lv['pillars']]


def walls(lv):
    return [(w['x'], w['z'], w['len'], w['axis'], w['h']) for w in lv['walls']]


def obstacles(lv):
    """The static occluders in shadow_design.py's format."""
    return ([('pillar', x, z, h) for x, z, h in pillars(lv)]
            + [('wall', x, z, ln, axis, h) for x, z, ln, axis, h in walls(lv)])
