from PodSixNet.Channel import Channel
from PodSixNet.Server import Server
from imports import *
from constants import *

class player_channel(Channel):
    def start(self,game):
        self.game=game
    def Network(self,data):
        self.game.mode.Network(self,data)

class cw_server(Server):
    channelClass = player_channel
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.channels=[]
        self.games=[]
    def Connected(self, channel, addr):
        self.channels+=channel
        if len(self.channels)%2==0:
            self.games.append(Game(self.channels[-1],self.channels[-2]))
    def tick(self,dt=0):
        self.Pump()
        for e in self.channels:
            e.Pump()
        for e in self.games:
            e.tick()

srvr=cw_server(localaddr=("192.168.1.132",5071))
pyglet.clock.schedule_interval(srvr.tick,1.0/60)
while True:
    pyglet.clock.tick()
