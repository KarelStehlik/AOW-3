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
                if is_empty_2d(data["troops"]):
                    return
                Formation(self.object_ID, data["instructions"], data["troops"], side, self)
                self.send_both({"action": "summon_formation", "tick": self.ticks, "side": side,
                                "instructions": data["instructions"], "troops": data["troops"],
                                "ID": self.object_ID})
                self.object_ID += 1
                return

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
        [e.tick() for e in self.walls]
        [e.tick() for e in self.formations]
        self.TownHall.tick()


##################   ---/core---  #################
##################   ---units---  ################# 
class TownHall:
    name = "TownHall"

    def __init__(self, x, y, side, game):
        self.x, self.y = x, y
        self.side = side
        self.size = unit_stats[self.name]["size"]
        self.hp = unit_stats[self.name]["hp"]
        self.game = game

    def tick(self):
        self.shove()

    def shove(self):
        for e in self.game.players[self.side - 1].units:
            if max(abs(e.x - self.x), abs(e.y - self.y)) < (self.size + e.size) / 2:
                dist_sq = (e.x - self.x) ** 2 + (e.y - self.y) ** 2
                if dist_sq < ((e.size + self.size) * .5) ** 2:
                    shovage = (e.size + self.size) * .5 * dist_sq ** -.5 - 1
                    e.take_knockback((e.x - self.x) * shovage, (e.y - self.y) * shovage, self)


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
        self.hp = self.maxhp = unit_stats[self.name]["hp"]
        game.players[side].towers.append(self)
        game.players[side].all_buildings.append(self)

    def die(self):
        self.game.players[self.side].towers.remove(self)
        self.game.players[self.side].all_buildings.remove(self)

    def take_damage(self, amount, source):
        self.hp -= amount
        if self.hp <= 0:
            self.die()
            return

    def tick(self):
        if self.spawning < FPS:
            self.spawning += 1
        if self.spawning == FPS:
            self.exists = True
            self.tick = self.tick2

    def tick2(self):
        self.shove()

    def delete(self):
        self.game.players[self.side].towers.remove(self)
        self.game.players[self.side].all_buildings.remove(self)

    def shove(self):
        for e in self.game.players[self.side - 1].units:
            if max(abs(e.x - self.x), abs(e.y - self.y)) < (self.size + e.size) / 2:
                dist_sq = (e.x - self.x) ** 2 + (e.y - self.y) ** 2
                if dist_sq < ((e.size + self.size) * .5) ** 2:
                    shovage = (e.size + self.size) * .5 * dist_sq ** -.5 - 1
                    e.take_knockback((e.x - self.x) * shovage, (e.y - self.y) * shovage, self)


class Wall:
    name = "Wall"

    def __init__(self, ID, t1, t2, side, game):
        self.exists = False
        self.spawning = 0
        self.hp = unit_stats[self.name]["hp"]
        self.width = unit_stats[self.name]["width"]
        self.ID = ID
        self.x1, self.y1, self.x2, self.y2 = t1.x, t1.y, t2.x, t2.y
        self.length = ((self.x1 - self.x2) ** 2 + (self.y1 - self.y2) ** 2) ** .5
        self.norm_vector = ((self.y2 - self.y1) / self.length, (self.x1 - self.x2) / self.length)
        self.line_c = -self.norm_vector[0] * self.x1 - self.norm_vector[1] * self.y1
        self.crossline_c = (-self.norm_vector[1] * (self.x1 + self.x2) + self.norm_vector[0] * (self.y1 + self.y2)) * .5
        self.side = side
        self.game = game
        game.players[side].walls.append(self)
        game.players[side].all_buildings.append(self)

    def die(self):
        self.game.players[self.side].walls.remove(self)
        self.game.players[self.side].all_buildings.remove(self)

    def take_damage(self, amount, source):
        self.hp -= amount
        if self.hp <= 0:
            self.die()
            return

    def shove(self):
        for e in self.game.players[1 - self.side].units:
            if point_line_dist(e.x, e.y, self.norm_vector, self.line_c) < (self.width + e.size) * .5 and \
                    point_line_dist(e.x, e.y, (self.norm_vector[1], -self.norm_vector[0]),
                                    self.crossline_c) < self.length * .5:
                shovage = point_line_dist(e.x, e.y, self.norm_vector, self.line_c) - (self.width + e.size) * .5
                if e.x * self.norm_vector[0] + e.y * self.norm_vector[1] + self.line_c > 0:
                    shovage *= -1
                e.take_knockback(self.norm_vector[0] * shovage, self.norm_vector[1] * shovage, self)

    def tick(self):
        if self.spawning < FPS:
            self.spawning += 1
        if self.spawning == FPS:
            self.exists = True
            self.tick = self.tick2

    def tick2(self):
        self.shove()

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
        self.x, self.y = self.game.players[self.side].TownHall.x, self.game.players[self.side].TownHall.y
        for column in range(UNIT_FORMATION_COLUMNS):
            for row in range(UNIT_FORMATION_ROWS):
                if troops[column][row] is not None:
                    self.troops.append(
                        possible_units[troops[column][row]](
                            i,
                            (column - self.game.unit_formation_columns / 2) * UNIT_SIZE + self.x,
                            (row - self.game.unit_formation_rows / 2) * UNIT_SIZE + self.y,
                            side,
                            column - self.game.unit_formation_columns / 2,
                            row - self.game.unit_formation_rows / 2,
                            game, self
                        )
                    )
                    i += 1
        self.instr_object = instruction_moving(self, self.x, self.y)
        self.aggro = {}

    def get_aggro(self, amount, source):
        if source in self.aggro:
            self.aggro[source] += amount
            return
        self.aggro[source] = amount

    def tick(self):
        if self.spawning < FPS:
            self.spawning += 1
        if self.spawning == FPS:
            self.exists = True
            self.tick = self.tick2
            [e.summon_done() for e in self.troops]

    def tick2(self):
        if self.instr_object.completed:
            if len(self.instructions) > 0:
                instruction = self.instructions.pop(0)
                if instruction[0] == "walk":
                    self.instr_object = instruction_moving(self, instruction[1], instruction[2])
            else:
                return
        self.instr_object.tick()
        for e in self.aggro:
            self.aggro[e]-=1
            if self.aggro[e]<=0:
                self.aggro.pop(e)

    def delete(self):
        self.game.players[self.side].formations.remove(self)


class instruction_moving:
    def __init__(self, formation, x, y):
        self.target = formation
        self.x, self.y = x, y
        self.dx, self.dy = x - formation.x, y - formation.y
        if self.dx == 0 == self.dy:
            self.completed = True
            return
        inv_hypot = (self.dx ** 2 + self.dy ** 2) ** -.5
        xr, yr = self.dx * inv_hypot * UNIT_SIZE, self.dy * inv_hypot * UNIT_SIZE
        for e in formation.troops:
            e.try_move(formation.x + e.column * yr + e.row * xr, formation.y - e.column * xr + e.row * yr)
        self.completed = False
        self.completed_rotate = False

    def tick(self):
        if self.completed:
            return
        [e.tick() for e in self.target.troops]
        if False not in [e.reached_goal for e in self.target.troops]:
            if self.completed_rotate:
                self.completed = True
                self.target.x, self.target.y = self.x, self.y
                return
            self.completed_rotate = True
            [e.try_move(e.x + self.dx, e.y + self.dy) for e in self.target.troops]


class Unit:
    name = "None"

    def __init__(self, ID, x, y, side, column, row, game, formation):
        self.ID = ID
        self.side = side
        self.game = game
        self.x, self.y = x, y
        self.column, self.row = column, row
        self.speed = unit_stats[self.name]["speed"] / FPS
        self.health = self.max_health = unit_stats[self.name]["hp"]
        self.damage = unit_stats[self.name]["dmg"]
        self.attack_cooldown = unit_stats[self.name]["cd"]
        self.exists = False
        self.rotation = 0
        self.game.players[self.side].units.append(self)
        self.desired_x, self.desired_y = x, y
        self.vx, self.vy = self.speed, 0
        self.reached_goal = True
        self.mass = 1
        self.size = unit_stats[self.name]["size"]

    def tick(self):
        pass

    def tick2(self):
        if self.reached_goal:
            return
        if self.x <= self.desired_x:
            self.x += min(self.vx, self.desired_x - self.x)
        else:
            self.x += max(self.vx, self.desired_x - self.x)
        if self.y <= self.desired_y:
            self.y += min(self.vy, self.desired_y - self.y)
        else:
            self.y += max(self.vy, self.desired_y - self.y)
        if self.y == self.desired_y and self.x == self.desired_x:
            self.reached_goal = True

    def rotate(self, x, y):
        if x == 0 == y:
            return
        inv_hypot = (x ** 2 + y ** 2) ** -.5
        if x == 0 == y:
            return
        if x >= 0:
            r = math.asin(x * inv_hypot)
        else:
            r = math.pi - math.asin(x * inv_hypot)
        self.rotation = r
        self.vx, self.vy = x * inv_hypot * self.speed, y * inv_hypot * self.speed

    def summon_done(self):
        self.exists = True
        self.tick = self.tick2

    def take_knockback(self, x, y, source):
        self.x += x
        self.y += y
        self.rotate(self.desired_x - self.x, self.desired_y - self.y)

    def try_move(self, x, y):
        if self.x == x and self.y == y:
            return
        self.desired_x, self.desired_y = x, y
        self.rotate(x - self.x, y - self.y)
        self.reached_goal = False

    def shove(self):
        # disabled - too much lag
        for e in self.game.players[self.side - 1].units:
            if max(abs(e.x - self.x), abs(e.y - self.y)) > (self.size + e.size) / 2:
                continue
            dist_sq = (e.x - self.x) ** 2 + (e.y - self.y) ** 2
            if dist_sq < ((e.size + self.size) * .5) ** 2:
                shovage = (e.size + self.size) * .5 * dist_sq ** -.5 - 1
                mass_ratio = self.mass / e.mass
                ex, ey, selfx, selfy = e.x, e.y, self.x, self.y
                e.take_knockback((ex - selfx) * shovage * mass_ratio, (ey - selfy) * shovage * mass_ratio)
                self.take_knockback((ex - selfx) * shovage * (mass_ratio - 1),
                                    (ey - selfy) * shovage * (mass_ratio - 1), self)
        for e in self.game.players[self.side].units:
            if max(abs(e.x - self.x), abs(e.y - self.y)) > (self.size + e.size) / 2 or e == self:
                continue
            dist_sq = (e.x - self.x) ** 2 + (e.y - self.y) ** 2
            if dist_sq < ((e.size + self.size) * .5) ** 2:
                shovage = (e.size + self.size) * .5 * dist_sq ** -.5 - 1
                mass_ratio = self.mass / (e.mass + self.mass)
                ex, ey, selfx, selfy = e.x, e.y, self.x, self.y
                e.take_knockback((ex - selfx) * shovage * mass_ratio, (ey - selfy) * shovage * mass_ratio)
                self.take_knockback((ex - selfx) * shovage * (mass_ratio - 1),
                                    (ey - selfy) * shovage * (mass_ratio - 1), self)


class Swordsman(Unit):
    name = "Swordsman"

    def __init__(self, ID, x, y, side, column, row, game, formation):
        super().__init__(ID, x, y, side, column, row, game, formation)


possible_units = [Swordsman]

##################  ---/units---  #################
