from PodSixNet.Channel import Channel
from PodSixNet.Server import Server
from imports import *
from constants import *

class player_channel(Channel):
    def start(self,game,side):
        self.game=game
        self.Send({"action":"start_game","side":side})
    def Network(self,data):
        self.game.network(data)

class cw_server(Server):
    channelClass = player_channel
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.channeles=[]
        self.games=[]
    def Connected(self, channel, addr):
        self.channeles.append(channel)
        if len(self.channels)%2==0:
            self.games.append(Game(self.channeles[-1],self.channeles[-2]))
    def tick(self,dt=0):
        self.Pump()
        for e in self.channels:
            e.Pump()
        for e in self.games:
            e.tick()

class Game():
    def __init__(self, channel1,channel2):
        channel1.start(self,0)
        channel2.start(self,1)
        self.channels=[channel1,channel2]
        self.buildings=[[],[]]
        self.units=[[],[]]
    def send_both(self,msg):
        self.channels[0].Send(msg)
        self.channels[1].Send(msg)
    def tick(self):
        pass
    def network(self,data):
        pass

srvr=cw_server(localaddr=("192.168.1.132",5071))
pyglet.clock.schedule_interval(srvr.tick,1.0/60)
while True:
    pyglet.clock.tick()
