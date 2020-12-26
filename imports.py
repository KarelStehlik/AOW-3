import pyglet
import numpy as np
from pyglet.gl import *
import time
import random
from pyglet.window import key
from pyglet import clock
import images
import os
from pyglet.gl import *
glEnable(GL_BLEND)
unit_stats={}
def load_stats():
    global unit_stats
    with open("stats.txt","r") as cs:
        units=cs.read().split("\n")
        for unit in units:
            name_stats=unit.split(":")
            stats={}
            for e in name_stats[1].split(","):
                k=e.split("=")
                stats[k[0]]=float(k[1])
            unit_stats[name_stats[0]]=stats
load_stats()
