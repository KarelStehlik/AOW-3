from imports import *
from constants import *


class Game:
    def __init__(self, channel1, channel2, server):
        channel1.start(self, 0)
        channel2.start(self, 1)
        self.time_start = time.time()
        self.channels = [channel1, channel2]
        self.players = [player(0, self), player(1, self)]
        self.server = server
        self.object_ID = 0
        self.ticks = 0
        self.unit_formation_columns = UNIT_FORMATION_COLUMNS
        self.unit_formation_rows = UNIT_FORMATION_ROWS

    def send_both(self, msg):
        self.channels[0].Send(msg)
        self.channels[1].Send(msg)

    def tick(self):
        while self.ticks < FPS * (time.time() - self.time_start):
            self.players[0].tick()
            self.players[1].tick()
            self.ticks += 1

    def network(self, data, side):
        if "action" in data:
            if data["action"] == "place_tower":
                self.players[side].towers.append(Tower(
                    self.object_ID, data["xy"][0], data["xy"][1], side, self))
                self.send_both({"action": "place_tower", "xy": data["xy"], "tick": self.ticks, "side": side,
                                "ID": self.object_ID})
                self.object_ID += 1
                return
            if data["action"] == "place_wall":
                t1, t2 = self.find_tower(data["ID1"], side), self.find_tower(data["ID2"], side)
                if None in [t1, t2] or t1 == t2:
                    return
                self.players[side].walls.append(Wall(
                    self.object_ID, t1, t2, side, self))
                self.send_both({"action": "place_wall", "ID1": data["ID1"],
                                "ID2": data["ID2"], "tick": self.ticks, "side": side,
                                "ID": self.object_ID})
                self.object_ID += 1
                return
            if data["action"] == "summon_formation":
                Formation(self.object_ID, data["instructions"], data["troops"], side, self)
                self.send_both({"action": "summon_formation", "tick": self.ticks, "side": side,
                                "instructions": data["instructions"], "troops": data["troops"],
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


class player:
    def __init__(self, side, game):
        self.side = side
        self.game = game
        self.walls = []
        self.units = []
        self.towers = []
        self.formations = []
        self.TownHall = TownHall(TH_DISTANCE * side, TH_DISTANCE * side, side, self.game)
        self.all_buildings = [self.TownHall]

    def tick(self):
        [e.tick() for e in self.units]
        [e.tick() for e in self.towers]
        [e.tick() for e in self.formations]


##################   ---/core---  #################
##################   ---units---  ################# 
class TownHall:
    name = "TownHall"

    def __init__(self, x, y, side, game):
        self.x, self.y = x, y
        self.side = side
        self.size = unit_stats[self.name]["size"]
        self.hp = unit_stats[self.name]["hp"]

    def tick(self):
        pass


class Tower:
    name = "Tower"

    def __init__(self, ID, x, y, side, game):
        self.game = game
        self.exists = False
        self.spawning = 0
        self.x, self.y = x, y
        self.ID = ID
        self.side = side
        self.size = unit_stats[self.name]["size"]
        self.hp = unit_stats[self.name]["hp"]
        game.players[side].towers.append(self)
        game.players[side].all_buildings.append(self)

    def tick(self):
        if self.spawning < FPS:
            self.spawning += 1
        if self.spawning == FPS:
            self.exists = True
            self.tick = self.tick2

    def tick2(self):
        pass

    def delete(self):
        self.game.players[self.side].towers.remove(self)
        self.game.players[self.side].all_buildings.remove(self)


class Wall:
    name = "Wall"

    def __init__(self, ID, t1, t2, side, game):
        self.exists = False
        self.spawning = 0
        self.hp = unit_stats[self.name]["hp"]
        self.width = unit_stats[self.name]["width"]
        self.ID = ID
        self.x1, self.y1, self.x2, self.y2 = t1.x, t1.y, t2.x, t2.y
        self.side = side
        self.game = game
        game.players[side].walls.append(self)
        game.players[side].all_buildings.append(self)

    def tick(self):
        if self.spawning < FPS:
            self.spawning += 1
        if self.spawning == FPS:
            self.exists = True
            self.tick = self.tick2

    def tick2(self):
        pass

    def delete(self):
        self.game.players[self.side].walls.remove(self)
        self.game.players[self.side].all_buildings.remove(self)


class Formation:
    def __init__(self, ID, instructions, troops, side, game):
        self.exists = False
        self.spawning = 0
        self.ID = ID
        self.instructions = instructions
        self.side = side
        self.game = game
        self.troops = []
        self.game.players[self.side].formations.append(self)
        i = 0
        for column in range(UNIT_FORMATION_COLUMNS):
            for row in range(UNIT_FORMATION_ROWS):
                if troops[column][row] is not None:
                    self.troops.append(
                        possible_units[troops[column][row]](
                            i,
                            (column - self.game.unit_formation_columns/2) * UNIT_SIZE +
                            self.game.players[self.side].TownHall.x,
                            (row - self.game.unit_formation_rows/2) * UNIT_SIZE +
                            self.game.players[self.side].TownHall.y,
                            side,
                            game
                        )
                    )
                    i += 1

    def tick(self):
        if self.spawning < FPS:
            self.spawning += 1
        if self.spawning == FPS:
            self.exists = True
            self.tick = self.tick2

    def tick2(self):
        pass

    def delete(self):
        self.game.players[self.side].formations.remove(self)


class Unit:
    name = "None"

    def __init__(self, ID, x, y, side, game):
        self.ID = ID
        self.side = side
        self.game = game
        self.x, self.y = x, y


class Swordsman(Unit):
    name = "Swordsman"

    def __init__(self, ID, x, y, side, game):
        super().__init__(ID, x, y, side, game)


possible_units = [Swordsman]

##################  ---/units---  #################
