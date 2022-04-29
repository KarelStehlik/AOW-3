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
        t0 = time.perf_counter()
        self.Pump()
        t1 = time.perf_counter()
        [e.Pump() for e in self.playing_channels]
        t2 = time.perf_counter()
        [e.tick() for e in self.games]
        t3 = time.perf_counter()
       # print(f"pump : {t1-t1}, channels : {t2-t1}, Game : {t3-t2}")


srvr = cw_server(localaddr=("192.168.1.237", 5071))
# srvr = cw_server(localaddr=("127.0.0.1", 5071))

# pyglet.clock.schedule_interval(srvr.tick, 1.0 / constants.FPS)
while True:
    srvr.tick()
