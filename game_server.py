from imports import *
from constants import *


class Game:
    def __init__(self, channel1, channel2, server):
        self.chunks = {}
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
        self.debug_secs, self.debug_ticks = time.time(), 0

    def send_both(self, msg):
        self.channels[0].Send(msg)
        self.channels[1].Send(msg)

    def clear_chunks(self):
        for e in self.chunks:
            self.chunks[e].clear_units()

    def tick(self):
        while self.ticks < FPS * (time.time() - self.time_start):
            self.clear_chunks()
            self.players[0].tick_units()
            self.players[1].tick_units()
            self.players[0].tick()
            self.players[1].tick()
            self.ticks += 1
            self.players[0].gain_money(PASSIVE_INCOME)
            self.players[1].gain_money(PASSIVE_INCOME)
            # self.debug_ticks += 1
            # if time.time() - self.debug_secs > 1:
            # self.debug_secs += 1
            # print(self.debug_ticks)
            # self.debug_ticks = 0

    def network(self, data, side):
        if "action" in data:
            if data["action"] == "place_tower":
                if self.players[side].attempt_purchase(Tower.get_cost([])):
                    Tower(self.object_ID, data["xy"][0], data["xy"][1], side, self)
                    self.send_both({"action": "place_tower", "xy": data["xy"], "tick": self.ticks, "side": side,
                                    "ID": self.object_ID})
                    self.object_ID += 1
            elif data["action"] == "place_wall":
                if self.players[side].attempt_purchase(Wall.get_cost([])):
                    t1, t2 = self.find_tower(data["ID1"], side), self.find_tower(data["ID2"], side)
                    if (None in [t1, t2]) or t1 == t2:
                        return
                    for e in self.players[0].walls:
                        if e.tower_1.ID in [data["ID1"], data["ID2"]] and e.tower_2.ID in [data["ID1"], data["ID2"]]:
                            return
                    for e in self.players[1].walls:
                        if e.tower_1.ID in [data["ID1"], data["ID2"]] and e.tower_2.ID in [data["ID1"], data["ID2"]]:
                            return
                    Wall(self.object_ID, t1, t2, side, self)
                    self.send_both({"action": "place_wall", "ID1": data["ID1"],
                                    "ID2": data["ID2"], "tick": self.ticks, "side": side,
                                    "ID": self.object_ID})
                    self.object_ID += 1
            elif data["action"] == "summon_formation":
                if self.players[side].attempt_purchase(Formation.get_cost([data["troops"], ])):
                    if is_empty_2d(data["troops"]):
                        return
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

    def add_unit_to_chunk(self, unit, location):
        if location in self.chunks:
            self.chunks[location].units[unit.side].append(unit)
            return
        self.chunks[location] = chunk()
        self.chunks[location].units[unit.side].append(unit)

    def add_tower_to_chunk(self, unit, location):
        if location in self.chunks:
            self.chunks[location].towers[unit.side].append(unit)
            return
        self.chunks[location] = chunk()
        self.chunks[location].towers[unit.side].append(unit)

    def add_townhall_to_chunk(self, unit, location):
        if location in self.chunks:
            self.chunks[location].townhalls[unit.side].append(unit)
            return
        self.chunks[location] = chunk()
        self.chunks[location].townhalls[unit.side].append(unit)

    def remove_unit_from_chunk(self, unit, location):
        self.chunks[location].units[unit.side].remove(unit)

    def remove_tower_from_chunk(self, unit, location):
        self.chunks[location].towers[unit.side].remove(unit)

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
        self.money = 0

    def gain_money(self, amount):
        self.money += amount

    def attempt_purchase(self, amount):
        if self.money < amount:
            return False
        self.money -= amount
        return True

    def tick_units(self):
        # ticks before other stuff to ensure the units are in their chunks
        [e.tick() for e in self.units]

    def tick(self):
        [e.tick() for e in self.towers]
        [e.tick() for e in self.walls]
        [e.tick() for e in self.formations]
        self.TownHall.tick()


class chunk:
    def __init__(self):
        self.units = [[], []]
        self.towers = [[], []]
        self.townhalls = [[], []]

    def is_empty(self):
        return self.units[0] == [] == self.units[1] and self.towers[0] == [] == self.towers[1]

    def clear_units(self):
        self.units = [[], []]

    def shove_units(self):
        for i in range(len(self.units[0])):
            for j in range(i):
                self.units[0][i].check_collision(self.units[0][j])
            for e in self.units[1]:
                self.units[0][i].check_collision(e)
        for i in range(len(self.units[1])):
            for j in range(i):
                self.units[1][i].check_collision(self.units[1][j])


##################   ---/core---  #################
##################   ---units---  #################
class TownHall:
    name = "TownHall"

    def __init__(self, x, y, side, game):
        self.entity_type = "townhall"
        self.x, self.y = x, y
        self.side = side
        self.size = unit_stats[self.name]["size"]
        self.hp = unit_stats[self.name]["hp"]
        self.game = game
        self.chunks = get_chunks(x, y, self.size)
        self.exists = True
        for e in self.chunks:
            game.add_townhall_to_chunk(self, e)

    def distance_to_point(self, x, y):
        return distance(self.x, self.y, x, y) - self.size / 2

    def take_damage(self, amount, source):
        if not self.exists:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.die()

    def die(self):
        print("game over")
        self.game.end(1 - self.side)

    def tick(self):
        self.shove()

    def shove(self):
        for c in self.chunks:
            for e in self.game.chunks[c].units[1 - self.side]:
                if e == self:
                    continue
                if max(abs(e.x - self.x), abs(e.y - self.y)) < (self.size + e.size) / 2:
                    dist_sq = (e.x - self.x) ** 2 + (e.y - self.y) ** 2
                    if dist_sq < ((e.size + self.size) * .5) ** 2:
                        shovage = (e.size + self.size) * .5 * dist_sq ** -.5 - 1
                        e.take_knockback((e.x - self.x) * shovage, (e.y - self.y) * shovage, self)


class Tower:
    name = "Tower"

    def __init__(self, ID, x, y, side, game):
        self.entity_type = "tower"
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
        self.chunks = get_chunks(x, y, self.size)
        for e in self.chunks:
            game.add_townhall_to_chunk(self, e)

    def distance_to_point(self, x, y):
        return distance(self.x, self.y, x, y) - self.size / 2

    @classmethod
    def get_cost(cls, params):
        return unit_stats[cls.name]["cost"]

    def die(self):
        self.game.players[self.side].towers.remove(self)
        self.game.players[self.side].all_buildings.remove(self)
        self.exists = False

    def take_damage(self, amount, source):
        if not self.exists:
            return
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
        for c in self.chunks:
            for e in self.game.chunks[c].units[1 - self.side]:
                if e == self:
                    continue
                if max(abs(e.x - self.x), abs(e.y - self.y)) < (self.size + e.size) / 2:
                    dist_sq = (e.x - self.x) ** 2 + (e.y - self.y) ** 2
                    if dist_sq < ((e.size + self.size) * .5) ** 2:
                        shovage = (e.size + self.size) * .5 * dist_sq ** -.5 - 1
                        e.take_knockback((e.x - self.x) * shovage, (e.y - self.y) * shovage, self)


class Wall:
    name = "Wall"

    def __init__(self, ID, t1, t2, side, game):
        self.entity_type = "wall"
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
        self.tower_1, self.tower_2 = t1, t2
        self.side = side
        self.game = game
        game.players[side].walls.append(self)
        game.players[side].all_buildings.append(self)

    def die(self):
        self.game.players[self.side].walls.remove(self)
        self.game.players[self.side].all_buildings.remove(self)

    @classmethod
    def get_cost(cls, params):
        return unit_stats[cls.name]["cost"]

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

    def towards(self, x, y):
        if point_line_dist(x, y, (self.norm_vector[1], -self.norm_vector[0]), self.crossline_c) < self.length * .5:
            if x * self.norm_vector[0] + y * self.norm_vector[1] + self.line_c < 0:
                return self.norm_vector
            return -self.norm_vector[0], -self.norm_vector[1]
        if (x - self.tower_1.x) ** 2 + (y - self.tower_1.y) ** 2 < (x - self.tower_2.x) ** 2 + (
                y - self.tower_2.y) ** 2:
            invh = inv_h(self.tower_1.x - x, self.tower_1.y - y)
            return (self.tower_1.x - x) * invh, (self.tower_1.y - y) * invh
        invh = inv_h(self.tower_2.x - x, self.tower_2.y - y)
        return (self.tower_2.x - x) * invh, (self.tower_2.y - y) * invh

    def distance_to_point(self, x, y):
        if point_line_dist(x, y, (self.norm_vector[1], -self.norm_vector[0]), self.crossline_c) < self.length * .5:
            return point_line_dist(x, y, self.norm_vector, self.line_c) - self.width / 2
        if (x - self.tower_1.x) ** 2 + (y - self.tower_1.y) ** 2 < (x - self.tower_2.x) ** 2 + (
                y - self.tower_2.y) ** 2:
            return distance(x, y, self.tower_1.x, self.tower_1.y) - self.width / 2
        return distance(x, y, self.tower_2.x, self.tower_2.y) - self.width / 2

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
        self.entity_type = "formation"
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
                if troops[column][row] != -1:
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
        self.all_targets = []

    @classmethod
    def get_cost(cls, params):
        cost = 0
        for column in range(UNIT_FORMATION_COLUMNS):
            for row in range(UNIT_FORMATION_ROWS):
                if params[0][column][row] != -1:
                    cost += possible_units[params[0][column][row]].get_cost([])
        return cost

    def tick(self):
        if self.spawning < FPS:
            self.spawning += 1
        if self.spawning == FPS:
            self.exists = True
            self.tick = self.tick2
            [e.summon_done() for e in self.troops]

    def tick2(self):
        i = 0
        while i < len(self.all_targets):
            if not self.all_targets[i].exists:
                self.all_targets.pop(i)
            else:
                i += 1
        if self.instr_object.completed:
            if len(self.instructions) > 0:
                instruction = self.instructions.pop(0)
                if instruction[0] == "walk":
                    self.desired_x, self.desired_y = instruction[1], instruction[2]
                    self.instr_object = instruction_moving(self, instruction[1], instruction[2])
            else:
                return
        self.instr_object.tick()

    def delete(self):
        self.game.players[self.side].formations.remove(self)
        self.instr_object.target = None
        self.instr_object = None

    def attack(self, enemy):
        if enemy.entity_type == "formation":
            enemy = enemy.troops
        else:
            enemy = [enemy, ]
        self.all_targets += enemy


class instruction:
    def __init__(self, formation, x, y):
        self.target = formation
        self.completed = False
        self.x, self.y = x, y


class instruction_linear(instruction):
    def __init__(self, formation, x, y):
        super().__init__(formation, x, y)
        dx, dy = x - formation.x, y - formation.y
        if dx == 0 == dy:
            self.completed = True
            return
        for e in formation.troops:
            e.try_move(dx + e.desired_x, dy + e.desired_y)

    def tick(self):
        if self.completed:
            return
        if False not in [e.reached_goal for e in self.target.troops]:
            self.completed = True
            self.target.x, self.target.y = self.x, self.y


class instruction_rotate(instruction):
    def __init__(self, formation, x, y):
        super().__init__(formation, x, y)
        dx, dy = x - formation.x, y - formation.y
        if dx == 0 == dy:
            self.completed = True
            return
        inv_hypot = inv_h(dx, dy)
        xr, yr = dx * inv_hypot * UNIT_SIZE, dy * inv_hypot * UNIT_SIZE
        for e in formation.troops:
            e.try_move(formation.x + e.column * yr + e.row * xr, formation.y + e.row * yr - e.column * xr)

    def tick(self):
        if self.completed:
            return
        if False not in [e.reached_goal for e in self.target.troops]:
            self.completed = True


class instruction_moving(instruction):
    def __init__(self, formation, x, y):
        super().__init__(formation, x, y)
        self.current = instruction_rotate(formation, x, y)
        self.stage = 0

    def tick(self):
        if self.completed:
            return
        self.current.tick()
        if self.current.completed:
            self.stage += 1
            if self.stage == 1:
                self.current = instruction_linear(self.target, self.x, self.y)
            elif self.stage == 2:
                self.completed = True


class Unit:
    name = "None"

    def __init__(self, ID, x, y, side, column, row, game, formation):
        self.entity_type = "unit"
        self.ID = ID
        self.lifetime = 0
        self.side = side
        self.game = game
        self.formation = formation
        self.x, self.y = x, y
        self.column, self.row = column, row
        self.game.players[self.side].units.append(self)
        self.size = unit_stats[self.name]["size"]
        self.speed = unit_stats[self.name]["speed"] / FPS
        self.health = self.max_health = unit_stats[self.name]["hp"]
        self.damage = unit_stats[self.name]["dmg"]
        self.attack_cooldown = unit_stats[self.name]["cd"]
        self.current_cooldown = 0
        self.reach = unit_stats[self.name]["reach"]
        self.exists = False
        self.target = None
        self.rotation = 0
        self.desired_x, self.desired_y = x, y
        self.vx, self.vy = self.speed, 0
        self.reached_goal = True
        self.mass = 1
        self.chunks = get_chunks(self.x, self.y, self.size)
        for e in self.chunks:
            self.game.add_unit_to_chunk(self, e)

    def distance_to_point(self, x, y):
        return distance(self.x, self.y, x, y) - self.size / 2

    @classmethod
    def get_cost(cls, params):
        return unit_stats[cls.name]["cost"]

    def take_damage(self, amount, source):
        if not self.exists:
            return
        self.health -= amount
        if self.health <= 0:
            self.die()

    def acquire_target(self):
        if self.target is not None and self.target.exists:
            return
        self.target = self.formation.all_targets[0]
        dist = self.target.distance_to_point(self.x, self.y) - self.size
        for e in self.formation.all_targets:
            new_dist = e.distance_to_point(self.x, self.y) - self.size
            if new_dist < dist:
                dist = new_dist
                self.target = e

    def move_in_range(self, other):
        if other.entity_type == "wall":
            d = other.distance_to_point(self.x, self.y)
            if d > self.reach:
                direction = other.towards(self.x, self.y)
                self.vx = self.speed * direction[0]
                self.vy = self.speed * direction[1]
                self.x += self.vx
                self.y += self.vy
            elif d < self.reach / 2:
                direction = other.towards(self.x, self.y)
                self.vx = -self.speed * direction[0] / 2
                self.vy = -self.speed * direction[1] / 2
                self.x += self.vx
                self.y += self.vy
            return d <= self.reach
        else:
            dist_sq = (other.x - self.x) ** 2 + (other.y - self.y) ** 2
            if dist_sq < ((other.size + self.size) * .5 + self.reach * 0.5) ** 2:
                self.rotate(self.x - other.x, self.y - other.y)
                self.vx /= 2
                self.vy /= 2
                self.x += self.vx
                self.y += self.vy
                return True
            elif dist_sq > ((other.size + self.size) * .5 + self.reach) ** 2:
                self.rotate(other.x - self.x, other.y - self.y)
                self.x += self.vx
                self.y += self.vy
            return dist_sq < ((other.size + self.size) * .5 + self.reach) ** 2

    def attempt_attack(self, target):
        if self.current_cooldown <= 0:
            self.current_cooldown += self.attack_cooldown
            self.attack(target)

    def attack(self, target):
        pass

    def die(self):
        self.exists = False
        self.formation.troops.remove(self)
        self.game.players[self.side].units.remove(self)
        self.game = None
        if not self.formation.troops:
            self.formation.delete()
        self.formation = None

    def tick(self):
        pass

    def tick2(self):
        if not self.exists:
            return
        if not self.formation.all_targets:
            x, y = self.x, self.y
            if self.reached_goal:
                pass
            else:
                self.rotate(self.desired_x - self.x, self.desired_y - self.y)
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
        else:
            self.acquire_target()
            if self.move_in_range(self.target):
                self.attempt_attack(self.target)

        self.chunks = get_chunks(self.x, self.y, self.size)
        for e in self.chunks:
            self.game.add_unit_to_chunk(self, e)
        self.shove()
        self.lifetime += 1
        if self.current_cooldown > 0:
            self.current_cooldown -= 1 / FPS

    def rotate(self, x, y):
        if x == 0 == y:
            return
        inv_hypot = inv_h(x, y)
        self.vx, self.vy = x * inv_hypot * self.speed, y * inv_hypot * self.speed

    def summon_done(self):
        self.exists = True
        self.tick = self.tick2

    def take_knockback(self, x, y, source):
        if not self.exists:
            return
        self.x += x
        self.y += y
        if source.entity_type == "unit" and source.side == 1 - self.side and source not in self.formation.all_targets:
            self.formation.attack(source.formation)
        elif source.entity_type == "tower" or source.entity_type == "townhall" \
                and source.side == 1 - self.side and source not in self.formation.all_targets:
            self.formation.attack(source)

    def try_move(self, x, y):
        if self.x == x and self.y == y:
            return
        self.desired_x, self.desired_y = x, y
        self.rotate(x - self.x, y - self.y)
        self.reached_goal = False

    def shove(self):
        if not self.exists:
            return
        for c in self.chunks:
            for e in self.game.chunks[c].units[self.side]:
                self.check_collision(e)
            for e in self.game.chunks[c].units[self.side - 1]:
                self.check_collision(e)

    def check_collision(self, other):
        if other.ID == self.ID:
            return
        if max(abs(other.x - self.x), abs(other.y - self.y)) < (self.size + other.size) / 2:
            dist_sq = (other.x - self.x) ** 2 + (other.y - self.y) ** 2
            if dist_sq < ((other.size + self.size) * .5) ** 2:
                shovage = (other.size + self.size) * .5 * dist_sq ** -.5 - 1  # desired dist / current dist -1
                mass_ratio = self.mass / (self.mass + other.mass)
                ex, sx, ey, sy = other.x, self.x, other.y, self.y
                other.take_knockback((ex - sx) * shovage * mass_ratio, (ey - sy) * shovage * mass_ratio,
                                     self)
                self.take_knockback((sx - ex) * shovage * (1 - mass_ratio),
                                    (sy - ey) * shovage * (1 - mass_ratio),
                                    other)


class Swordsman(Unit):
    name = "Swordsman"

    def __init__(self, ID, x, y, side, column, row, game, formation):
        super().__init__(ID, x, y, side, column, row, game, formation)

    def attack(self, target):
        target.take_damage(self.damage, self)


class Archer(Unit):
    name = "Archer"

    def __init__(self, ID, x, y, side, column, row, game, formation):
        super().__init__(ID, x, y, side, column, row, game, formation)

    def attack(self, target):
        target.take_damage(self.damage, self)


possible_units = [Swordsman, Archer]

##################  ---/units---  #################
