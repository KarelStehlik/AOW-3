import pyglet
from imports import unit_stats
import os
import time

pyglet.options['audio'] = ('directsound', 'xaudio2', 'openal', 'pulse', 'silent')


def load(name):
    return pyglet.media.load(f"noise/{name}.mp3", streaming=False)


sounds = {}
actions = ("spawn", "die", "attack")

for unit in unit_stats.keys():
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
                sounds[name][act].append(pyglet.media.load("noise/" + file, streaming=False))

for unit in unit_stats.keys():
    for act in actions:
        sounds[unit][act] = tuple(sounds[unit][act])

bgm = load("spectre")
arrow_launched = load("bow_pew")
building_destroyed = load("building_destroyed")

if __name__ == "__main__":
    bgm.play()

    while True:
        a = 100 ** 500000
        pyglet.clock.tick()
