from PodSixNet.Channel import Channel
from PodSixNet.Server import Server
from imports import *
import game_server as game_stuff


class player_channel(Channel):
    def __init__(self, conn=None, addr=(), server=None, map=None):
        super().__init__(conn=conn, addr=addr, server=server, map=map)
        self.game = None
        self.server = None

    def set_server(self, server):
        self.server = server

    def conn(self):
        if self.server is not None:
            self.server.join(self)

    def dis(self):
        if self.server is not None:
            self.server.leave(self)

    def start(self, game, side):
        self.game = game
        self.side = side
        self.Send({"action": "start_game", "side": side, "time0": str(time.time())})

    def Network(self, data):
        if self.game is not None:
            self.game.network(data, self.side)

    def Network_join(self, data):
        self.conn()


class cw_server(Server):
    channelClass = player_channel

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.playing_channels = []
        self.all_channels = []
        self.games = []

    def Connected(self, channel, addr):
        self.all_channels.append(channel)
        channel.set_server(self)

    def join(self, channel):
        if channel not in self.playing_channels:
            self.playing_channels.append(channel)
            if len(self.playing_channels) % 2 == 0:
                self.games.append(game_stuff.Game(self.playing_channels[-1],
                                                  self.playing_channels[-2], self))

    def leave(self, channel):
        pass

    def tick(self, dt=0):
        self.Pump()
        [e.Pump() for e in self.playing_channels]
        [e.tick() for e in self.games]


srvr = cw_server(localaddr=("192.168.1.237", 5071))
# srvr = cw_server(localaddr=("127.0.0.1", 5071))

# pyglet.clock.schedule_interval(srvr.tick, 1.0 / constants.FPS)
while True:
    srvr.tick()
    time.sleep(0.001)
