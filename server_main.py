from PodSixNet.Channel import Channel
from PodSixNet.Server import Server
from imports import *
from constants import *

class player_channel(Channel):
    def __init__(self, conn=None, addr=(), server=None, map=None):
        super().__init__(conn=conn, addr=addr, server=server, map=map)
        self.game=None
        self.server=None
    def set_server(self,server):
        self.server=server
    def conn(self):
        if self.server!=None:
            self.server.join(self)
    def dis(self):
        if self.server!=None:
            self.server.leave(self)
    def start(self,game,side):
        self.game=game
        self.Send({"action":"start_game","side":side})
    def Network(self,data):
        if self.game!=None:
            self.game.network(data)
    def Network_join(self,data):
        self.conn()

class cw_server(Server):
    channelClass = player_channel
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.playing_channels=[]
        self.all_channels=[]
        self.games=[]
    def Connected(self, channel, addr):
        self.all_channels.append(channel)
        channel.set_server(self)
    def join(self,channel):
        if not channel in self.playing_channels:
            self.playing_channels.append(channel)
            if len(self.playing_channels)%2==0:
                self.games.append(Game(self.playing_channels[-1],self.playing_channels[-2],self))
    def leave(self,channel):
        pass
    def tick(self,dt=0):
        self.Pump()
        for e in self.playing_channels:
            e.Pump()
        for e in self.games:
            e.tick()

class Game():
    def __init__(self, channel1,channel2,server):
        channel1.start(self,0)
        channel2.start(self,1)
        self.channels=[channel1,channel2]
        self.buildings=[[],[]]
        self.units=[[],[]]
        self.server=server
    def send_both(self,msg):
        self.channels[0].Send(msg)
        self.channels[1].Send(msg)
    def tick(self):
        pass
    def network(self,data):
        pass
    def end(self,winner):
        self.send_both({"action":"game_end","winner":winner})
        self.server.games.remove(self)
        self.server.playing_channels.remove(channels[0])
        self.server.playing_channels.remove(channels[1])

srvr=cw_server(localaddr=("192.168.1.132",5071))
pyglet.clock.schedule_interval(srvr.tick,1.0/60)
while True:
    pyglet.clock.tick()
