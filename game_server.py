from imports import *


class Game():
    def __init__(self, channel1, channel2, server):
        channel1.start(self, 0)
        channel2.start(self, 1)
        self.time_start = time.time()
        self.channels = [channel1, channel2]
        self.players = [player(), player()]
        self.server = server
        self.object_ID = 0
        self.ticks = 0

    def send_both(self, msg):
        self.channels[0].Send(msg)
        self.channels[1].Send(msg)

    def tick(self):
        self.players[0].tick()
        self.players[1].tick()
        self.ticks += 1

    def network(self, data, side):
        if "action" in data:
            if data["action"] == "place_tower":
                self.players[side].towers.append(Tower(
                    self.object_ID, data["xy"][0], data["xy"][1], side, self))
                self.send_both({"action": "place_tower", "xy": data["xy"], "side": side,
                                "ID": self.object_ID})
                self.object_ID += 1
            if data["action"] == "place_wall":
                t1, t2 = self.find_tower(data["ID1"], side), self.find_tower(data["ID2"], side)
                if None in [t1, t2] or t1 == t2:
                    return
                self.players[side].walls.append(Wall(
                    self.object_ID, t1, t2, side, self))
                self.send_both({"action": "place_wall", "ID1": data["ID1"],
                                "ID2": data["ID2"], "side": side,
                                "ID": self.object_ID})
                self.object_ID += 1

    def end(self, winner):
        self.send_both({"action": "game_end", "winner": winner})
        self.server.games.remove(self)
        self.server.playing_channels.remove(self.channels[0])
        self.server.playing_channels.remove(self.channels[1])

    def find_tower(self, ID, side):
        for e in self.players[side].towers:
            if e.ID == ID:
                return e
        return None

    def find_wall(self, ID, side):
        for e in self.players[side].walls:
            if e.ID == ID:
                return e
        return None

    def find_unit(self, ID, side):
        for e in self.players[side].units:
            if e.ID == ID:
                return e
        return None


class player():
    def __init__(self):
        self.walls = []
        self.units = []
        self.towers = []

    def tick(self):
        [e.tick() for e in self.units]
        [e.tick() for e in self.towers]


##################   ---/core---  #################
##################   ---units---  ################# 

class Tower():
    name = "Tower"

    def __init__(self, ID, x, y, side, game):
        self.x, self.y = x, y
        self.ID = ID
        self.side = side
        self.size = unit_stats[self.name]["size"]
        self.hp = unit_stats[self.name]["hp"]
        self.l = game.players[side].towers
        self.l.append(self)

    def tick(self):
        pass


class Wall():
    name = "Wall"

    def __init__(self, ID, t1, t2, side, game):
        self.hp = unit_stats[self.name]["hp"]
        self.width = unit_stats[self.name]["width"]
        self.ID = ID
        self.x1, self.y1, self.x2, self.y2 = t1.x, t1.y, t2.x, t2.y
        self.side = side
        self.game = game
        self.l = game.players[side].walls
        self.l.append(self)

##################  ---/units---  #################
