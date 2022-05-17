import pyglet
from imports import unit_stats
import os
import time
import constants
import random

pyglet.options['audio'] = ('directsound', 'xaudio2', 'openal', 'pulse', 'silent')


def load(name):
    return pyglet.media.load(f"noise/sounds/{name}.mp3", streaming=False)


'''for unit in unit_stats.keys():
    sounds[unit] = {}
    for act in actions:
        sounds[unit][act] = []

for root, dirs, files in os.walk("noise/"):
    for file in files:
        split = file.split(".")[0].split("_")
        if split[0] in actions:
            names = [e.capitalize() for e in split[1:-1]]
            act = split[0]
            for name in names:
                sounds[name][act].append(pyglet.media.load("noise/" + file, streaming=False))'''

loaded_sounds = {}

for root, dirs, files in os.walk("noise/sounds/"):
    for file in files:
        name = file.split(".")[0]
        loaded_sounds[name] = load(name)

sounds = {}
with open("noise/unit_sounds.txt", "r") as cs:
    lines = cs.read().split("\n")
    for unit in lines:
        name_stats = unit.split(":")
        stats = {}
        for e in name_stats[1].split(","):
            if e != "":
                k = e.split("=")
                stats[k[0]] = []
                for name in k[1].split("|"):
                    stats[k[0]].append(loaded_sounds[name])
        sounds[name_stats[0]] = stats


def play(unit_name, action, volume=constants.SFX):
    unit = sounds[unit_name]
    if action in unit and unit[action]:
        random.choice(unit[action]).play().volume = volume


bgm = load("spectre")
# bgm = load("bow_pew")

TH_death = load("TownHall_dies")

arrow_launched = load("bow_pew")
building_destroyed = load("building_destroyed")

if __name__ == "__main__":
    p = pyglet.media.player.Player()
    p.loop = True
    p.queue(bgm)
    p.play()

    while True:
        a = 100 ** 500000
        t = time.perf_counter()
        pyglet.app.platform_event_loop.step(0)
        pyglet.clock.tick()
        print(time.perf_counter() - t)
