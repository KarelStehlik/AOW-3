import pyglet
import time
import random
from pyglet.window import key
from pyglet import clock
import os
import math
from numba import jit
import constants

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


@jit(nopython=True)
def get_chunks(x, y, size):
    #return [[int(x // constants.CHUNK_SIZE), int(y // constants.CHUNK_SIZE)]]
    minx = (x - size*.5) // constants.CHUNK_SIZE
    miny = (y - size*.5) // constants.CHUNK_SIZE
    maxx = (x + size*.5) // constants.CHUNK_SIZE
    maxy = (y + size*.5) // constants.CHUNK_SIZE
    chunks=[str(a) + " " + str(b) for a in range(minx,maxx+1) for b in range(miny,maxy+1)]
    return chunks
