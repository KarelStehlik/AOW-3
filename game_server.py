from imports import *
import groups
from constants import *

class Game():
    def __init__(self, channel1,channel2,server):
        channel1.start(self,0)
        channel2.start(self,1)
        self.channels=[channel1,channel2]
        self.players=[player(),player()]
        self.server=server
    def send_both(self,msg):
        self.channels[0].Send(msg)
        self.channels[1].Send(msg)
    def tick(self):
        self.players[0].tick()
        self.players[1].tick()
    def network(self,data,side):
        if "action" in data:
            if data["action"]=="place_tower":
                self.players[side].towers.append(Tower(
                        data["xy"][0],data["xy"][1],side,self ))
                self.send_both({"action":"place_tower","xy":data["xy"],"side":side})
    def end(self,winner):
        self.send_both({"action":"game_end","winner":winner})
        self.server.games.remove(self)
        self.server.playing_channels.remove(channels[0])
        self.server.playing_channels.remove(channels[1])

class player():
    def __init__(self):
        self.walls=[]
        self.units=[]
        self.towers=[]
    def tick(self):
        [e.tick() for e in self.units]
        [e.tick for e in self.towers]

class Tower():
    name="Tower"
    def __init__(self,x,y,side,game):
        self.x,self.y=x,y
        self.side=side
        self.size=unit_stats[self.name]["size"]
        self.l=game.players[side].towers
        self.l.append(self)
    def tick(self):
        pass
