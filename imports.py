import numba
import pyglet
import time
import random
from pyglet.window import key
from pyglet import clock
import os
import math
from numba import njit, float64
import constants
import cProfile
import pstats
import numpy as np

# import tensorflow

pyglet.gl.glEnable(pyglet.gl.GL_BLEND)


@njit
def distance(x1, y1, x2, y2):
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** .5


distance(1.1, 1.1, 1.1, 1.1)
distance(1, 1, 1, 1)


@njit
def distance_squared(x1, y1, x2, y2):
    return (x1 - x2) ** 2 + (y1 - y2) ** 2


distance_squared(1.1, 1.1, 1.1, 1.1)
distance_squared(1, 1, 1, 1)


@njit
def hypot(x, y):
    return (x ** 2 + y ** 2) ** .5


hypot(1.1, 1.1)
hypot(1, 1)


@njit
def hypot_squared(x, y):
    return x ** 2 + y ** 2


hypot_squared(1.1, 1.1)
hypot_squared(1, 1)


def load_stats():
    unit_statst = {}
    with open("stats.txt", "r") as cs:
        units = cs.read().split("\n")
        for unit in units:
            name_stats = unit.split(":")
            stats = {}
            for e in name_stats[1].split(","):
                k = e.split("=")
                if k[0].startswith("cost"):
                    stats[k[0]] = int(k[1])

                    stats[k[0]]=1

                else:
                    stats[k[0]] = float(k[1])

                    stats[k[0]] = 1

                if k[0] == "speed":
                    stats[k[0]] /= constants.FPS
            if "resistance" not in stats.keys():
                stats["resistance"] = 1
            unit_statst[name_stats[0]] = stats
    return unit_statst


unit_stats = load_stats()


def load_items():
    items = {}
    weight = 0
    with open("items.txt", "r") as cs:
        units = cs.read().split("\n")
        for unit in units:
            name_stats = unit.split(":")
            stats = {}
            for e in name_stats[1].split(","):
                k = e.split("=")
                if k[0].startswith("cost"):
                    stats[k[0]] = int(k[1])
                elif k[0] == "weight":
                    w = int(k[1])
                    stats[k[0]] = w
                    weight += w
                else:
                    stats[k[0]] = float(k[1])
            items[name_stats[0]] = stats
    return weight, items


merchant_total_weight, merchant_items = load_items()


def get_merchant_items(seed, count):
    random.seed(seed)
    result = []
    for _ in range(count):
        w = random.randint(0, merchant_total_weight)
        for key, value in merchant_items.items():
            w -= value["weight"]
            if w < 0:
                result.append(key)
                break
    return result


def load_tags():
    tagges = {}
    with open("tags.txt", "r") as cs:
        units = cs.read().split("\n")
        for unit in units:
            name_stats = unit.split(":")
            tags = []
            for e in name_stats[1].split(","):
                tags.append(e)
            tagges[name_stats[0]] = tags
    return tagges


unit_tags = load_tags()


def has_tag(name, tag):
    if name not in unit_tags:
        return False
    return tag in unit_tags[name]


def has_all_tags(name, tags):
    if name not in unit_tags:
        return False
    for e in tags:
        if not has_tag(name, e):
            return False
    return True


def has_some_tag(name, tags):
    if name not in unit_tags:
        return False
    for e in tags:
        if has_tag(name, e):
            return True
    return False


def has_tags(name, tags, any_tag):
    if any_tag:
        return has_some_tag(name, tags)
    return has_all_tags(name, tags)


def load_upgrades():
    unit_statst = {}
    with open("upgrade_descriptions.txt", "r") as cs:
        units = cs.read().split("\n")
        for unit in units:
            name_stats = unit.split(":")
            stats = {}
            for e in name_stats[1].split("|"):
                k = e.split("=")
                stats[k[0]] = k[1]
                if True:#constants.CHEATS and k[0] == "time":
                    stats[k[0]] = "1"
            del e
            unit_statst[name_stats[0]] = stats
    return unit_statst


upgrade_stats = load_upgrades()


def is_empty_2d(l):
    for e in l:
        if e:
            return False
    return True


@njit
def average(*a):
    s = 0
    for e in a:
        s += e
    return s / len(a)


average(*[1.1, 1.1, 1.2])


@njit
def point_line_dist(x, y, normal_vector, c):
    # assumes vector is normalized
    return abs(x * normal_vector[0] + y * normal_vector[1] + c)


point_line_dist(1.1, 1.1, (1.1, 1.1), 1.1)


@njit
def get_chunks(x, y, size):
    # return [[int(x * constants.INV_CHUNK_SIZE), int(y * constants.INV_CHUNK_SIZE)]]
    size /= 2
    minx = math.floor((x - size) * constants.INV_CHUNK_SIZE)
    miny = math.floor((y - size) * constants.INV_CHUNK_SIZE)
    maxx = math.floor((x + size) * constants.INV_CHUNK_SIZE)
    maxy = math.floor((y + size) * constants.INV_CHUNK_SIZE)
    chunks = [(a, b) for a in range(minx, maxx + 1) for b in range(miny, maxy + 1)]
    return chunks


get_chunks(1.1, 1.1, 1.1)


@njit
def get_chunks_force_circle(x, y, size):
    # return [[int(x * constants.INV_CHUNK_SIZE), int(y * constants.INV_CHUNK_SIZE)]]
    size /= 2
    minx = math.floor((x - size) * constants.INV_CHUNK_SIZE)
    miny = math.floor((y - size) * constants.INV_CHUNK_SIZE)
    maxx = math.floor((x + size) * constants.INV_CHUNK_SIZE)
    maxy = math.floor((y + size) * constants.INV_CHUNK_SIZE)
    chunks = [(a, b) for a in range(minx, maxx + 1) for b in range(miny, maxy + 1)]
    i = 0
    while i < len(chunks):
        if (x - (chunks[i][0] + .5) * constants.CHUNK_SIZE) ** 2 + (
                y - (chunks[i][1] + .5) * constants.CHUNK_SIZE) ** 2 > (size + constants.CHUNK_SIZE * .8) ** 2:
            chunks.pop(i)
            i -= 1
        i += 1
    return chunks


get_chunks_force_circle(1.1, 1.1, 1.1)


def get_chunks_spiral(x, y, size):
    # return [[int(x * constants.INV_CHUNK_SIZE), int(y * constants.INV_CHUNK_SIZE)]]
    chunks = get_chunks(x, y, size)

    chunks.sort(
        key=lambda chunk: distance(constants.CHUNK_SIZE * (chunk[0] + .5), constants.CHUNK_SIZE * (chunk[1] + .5), x,
                                   y))
    return chunks


get_chunks_spiral(1.1, 1.1, 1.4)


@njit
def get_chunks_force_circle_sorted(x, y, size):
    # return [[int(x * constants.INV_CHUNK_SIZE), int(y * constants.INV_CHUNK_SIZE)]]
    size /= 2
    minx = math.floor((x - size) * constants.INV_CHUNK_SIZE)
    miny = math.floor((y - size) * constants.INV_CHUNK_SIZE)
    maxx = math.floor((x + size) * constants.INV_CHUNK_SIZE)
    maxy = math.floor((y + size) * constants.INV_CHUNK_SIZE)
    chunks = [(a, b) for a in range(minx, maxx + 1) for b in range(miny, maxy + 1)]
    i = 0
    while i < len(chunks):
        if (x - (chunks[i][0] + .5) * constants.CHUNK_SIZE) ** 2 + (
                y - (chunks[i][1] + .5) * constants.CHUNK_SIZE) ** 2 > (size + constants.CHUNK_SIZE * .8) ** 2:
            chunks.pop(i)
            i -= 1
        i += 1
    return chunks


get_chunks_force_circle(1.1, 1.1, 1.1)


@njit
def get_chunk(x, y):
    x = math.floor(x * constants.INV_CHUNK_SIZE)
    y = math.floor(y * constants.INV_CHUNK_SIZE)
    return (x, y)


get_chunk(1.1, 1.1)


@njit
def get_wall_chunks(x1, y1, x2, y2, norm, c, size):
    re = []
    size /= 2
    max_x = (max(x1, x2) * constants.INV_CHUNK_SIZE + 1) * constants.CHUNK_SIZE
    min_x = (min(x1, x2) * constants.INV_CHUNK_SIZE) * constants.CHUNK_SIZE
    max_y = (max(y1, y2) * constants.INV_CHUNK_SIZE + 1) * constants.CHUNK_SIZE
    min_y = (min(y1, y2) * constants.INV_CHUNK_SIZE) * constants.CHUNK_SIZE
    n1 = max(abs(norm[0]), abs(norm[1]))
    n0 = min(abs(norm[0]), abs(norm[1]))
    rotation_factor = .5 / n1 + n0 * (.5 - n0 / n1 / 2)
    for x in range(min_x + constants.CHUNK_SIZE / 2, max_x, constants.CHUNK_SIZE):
        for y in range(min_y + constants.CHUNK_SIZE / 2, max_y, constants.CHUNK_SIZE):
            if abs(x * norm[0] + y * norm[1] + c) < size + constants.CHUNK_SIZE * rotation_factor:
                re.append(get_chunk(x, y))
    return re


get_wall_chunks(-164.42324829101562, 283.2799987792969, 360.5767517089844, 310.2799987792969,
                (0.05136069438302041, -0.9986801685587303), 291.35100913516345, 30.0)


@njit
def get_rotation(x, y):
    inv_hypot = (x ** 2 + y ** 2) ** -.5
    if x >= 0:
        return math.asin(max(min(y * inv_hypot, 1), -1))
    return math.pi - math.asin(max(min(y * inv_hypot, 1), -1))


get_rotation(1.1, 1.1)


@njit
def get_rotation_norm(x, y):
    if x >= 0:
        return math.asin(max(min(y, 1), -1))
    return math.pi - math.asin(max(min(y, 1), -1))


get_rotation_norm(.1, .1)


@njit
def inv_h(x, y):
    return (x ** 2 + y ** 2) ** -.5


inv_h(1.1, 1.1)


@njit  # (List(float64))
def product(*a):
    if len(a) == 0:
        return 1.0
    p = 1.0
    for e in a:
        p *= e
    return p


product(1.2, 1.3, 1.2)
