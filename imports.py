import pyglet
import time
import random
from pyglet.window import key
from pyglet import clock
import os
import math
from numba import njit
from numba.experimental import jitclass
import constants
from functools import cache

pyglet.gl.glEnable(pyglet.gl.GL_BLEND)


def load_stats():
    unit_statst = {}
    with open("stats.txt", "r") as cs:
        units = cs.read().split("\n")
        for unit in units:
            name_stats = unit.split(":")
            stats = {}
            for e in name_stats[1].split(","):
                k = e.split("=")
                stats[k[0]] = float(k[1])
            del e
            unit_statst[name_stats[0]] = stats
    return unit_statst


unit_stats = load_stats()


def is_empty_2d(l):
    for e in l:
        if e:
            return False
    return True


def point_line_dist(x, y, normal_vector, c):
    # assumes vector is normalized
    return abs(x * normal_vector[0] + y * normal_vector[1] + c)


@njit
def get_chunks(x, y, size):
    # return [[int(x // constants.CHUNK_SIZE), int(y // constants.CHUNK_SIZE)]]
    minx = int((x - size * .5) // constants.CHUNK_SIZE)
    miny = int((y - size * .5) // constants.CHUNK_SIZE)
    maxx = int((x + size * .5) // constants.CHUNK_SIZE)
    maxy = int((y + size * .5) // constants.CHUNK_SIZE)
    chunks = [str(a) + " " + str(b) for a in range(minx, maxx + 1) for b in range(miny, maxy + 1)]
    return chunks


get_chunks(1.1, 1.1, 1.1)


@njit
def get_rotation(x, y):
    inv_hypot = (x ** 2 + y ** 2) ** -.5
    if x >= 0:
        return math.asin(max(min(y * inv_hypot, 1), -1))
    return math.pi - math.asin(max(min(y * inv_hypot, 1), -1))


get_rotation(1.1, 1.1)


@njit
def inv_h(x, y):
    return (x ** 2 + y ** 2) ** -.5


inv_h(1.1, 1.1)


@njit
def distance(x1, y1, x2, y2):
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** .5


distance(1.1, 1.1, 1.1, 1.1)
