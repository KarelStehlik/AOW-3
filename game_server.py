from imports import *
from constants import *


def generate_units(money):
    original_money = money
    units = [[-1 for _ in range(UNIT_FORMATION_ROWS)] for _ in range(UNIT_FORMATION_COLUMNS)]

    # units[1][1]=len(possible_units)-1
    # return units, 1
    # units[1][1] = 1
    # money-=possible_units[1].get_cost([])
    # return units, original_money / (original_money - money)

    big, medium, small = [], [], []
    for e in possible_units:
        if e.get_cost([]) >= 2000:
            big.append(e)
        elif e.get_cost([]) <= 100:
            small.append(e)
        else:
            medium.append(e)
    for x in range(UNIT_FORMATION_COLUMNS):
        for y in range(UNIT_FORMATION_ROWS):
            if money > 10000:
                choice = random.choice(big)
            elif money > 1000:
                choice = random.choice(medium)
            elif money > 0:
                choice = random.choice(small)
            else:
                return units, original_money / (original_money - money)
            money -= choice.get_cost([])
            units[x][y] = possible_units.index(choice)
    return units, original_money / (original_money - money)


class Game:
    def __init__(self, channel1, channel2, server):
        self.chunks = {}
        channel1.start(self, 0)
        channel2.start(self, 1)
        self.time_start = time.time()
        self.channels = [channel1, channel2]
        self.players = [player(0, self), player(1, self)]
        for e in self.players:
            e.summon_townhall()
        self.server = server
        self.object_ID = 0
        self.ticks = 0
        self.unit_formation_columns = UNIT_FORMATION_COLUMNS
        self.unit_formation_rows = UNIT_FORMATION_ROWS
        self.debug_secs, self.debug_ticks = time.time(), 0
        self.projectiles = []

    def send_both(self, msg):
        self.channels[0].Send(msg)
        self.channels[1].Send(msg)

    def clear_chunks(self):
        for e in self.chunks:
            self.chunks[e].clear_units()

    def tick(self):
        while self.ticks < FPS * (time.time() - self.time_start):
            odd_tick = self.ticks % 2
            self.clear_chunks()
            self.players[odd_tick].tick_units()
            self.players[odd_tick - 1].tick_units()
            self.players[odd_tick].tick()
            self.players[odd_tick - 1].tick()
            [e.tick() for e in self.projectiles]
            self.ticks += 1
            self.players[0].gain_money(PASSIVE_INCOME)
            self.players[1].gain_money(PASSIVE_INCOME)
            self.players[odd_tick].tick_wave_timer()
            self.players[odd_tick - 1].tick_wave_timer()
            # if self.ticks % 200 == 0:
            #    print(self.ticks, len(self.players[0].units), len(self.players[1].units), self.players[0].money,
            #          self.players[1].money, time.time() - self.time_start)
            # self.debug_ticks += 1
            # if time.time() - self.debug_secs > 1:
            # self.debug_secs += 1
            # print(self.debug_ticks)
            # self.debug_ticks = 0

    def network(self, data, side):
        if "action" in data:
            if data["action"] == "place_building":
                entity_type = possible_buildings[data["entity_type"]]
                close_to_friendly = False
                proximity = unit_stats[entity_type.name]["proximity"]
                for e in self.players[side].all_buildings:
                    if e.distance_to_point(*data["xy"]) < proximity:
                        close_to_friendly = True
                if not close_to_friendly:
                    return
                for e in self.players[1].all_buildings:
                    if e.distance_to_point(*data["xy"]) < unit_stats[entity_type.name]["size"] / 2:
                        return
                for e in self.players[0].all_buildings:
                    if e.distance_to_point(*data["xy"]) < unit_stats[entity_type.name]["size"] / 2:
                        return
                if self.players[side].attempt_purchase(entity_type.get_cost([])):
                    entity_type(self.object_ID, data["xy"][0], data["xy"][1], side, self)
                    self.send_both({"action": "place_building", "xy": data["xy"], "tick": self.ticks, "side": side,
                                    "ID": self.object_ID, "entity_type": data["entity_type"]})
                    # print({"action": "place_building", "xy": data["xy"], "tick": self.ticks, "side": side,
                    #       "ID": self.object_ID, "entity_type": data["entity_type"]})
                    self.object_ID += 1
            elif data["action"] == "place_wall":
                if self.players[side].attempt_purchase(Wall.get_cost([])):
                    t1, t2 = self.find_building(data["ID1"], side, "tower"), self.find_building(data["ID2"], side,
                                                                                                "tower")
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
                    oid = self.object_ID
                    Formation(oid, data["instructions"], data["troops"], side, self)
                    self.send_both({"action": "summon_formation", "tick": self.ticks, "side": side,
                                    "instructions": data["instructions"], "troops": data["troops"],
                                    "ID": oid})
                    self.object_ID += 1
            elif data["action"] == "buy upgrade":
                target = self.find_building(data["building ID"], side)
                if target is None or len(target.upgrades_into) <= data["upgrade num"]:
                    return
                if target is not None and target.exists and self.players[side].attempt_purchase(
                        target.upgrades_into[data["upgrade num"]].get_cost([])):
                    target.upgrades_into[data["upgrade num"]](target)
                    self.send_both({"action": "upgrade", "tick": self.ticks, "side": side, "ID": data["building ID"],
                                    "upgrade num": data["upgrade num"],
                                    "backup": [possible_buildings.index(target.upgrades_into[data["upgrade num"]]),
                                               target.x, target.y, self.ticks, side, target.ID]})
                    target.upgrades_into = []
            elif data["action"] == "ping":
                self.channels[side].Send({"action": "pong", "time": str(time.time())})
            elif data["action"] == "send_wave":
                for e in self.players[1 - side].formations:
                    if e.AI:
                        return
                self.summon_ai_wave(side)

    def summon_ai_wave(self, side):
        self.players[side].ai_wave += 1
        power = 1000 * self.players[side].ai_wave ** 1.8
        worth = power
        self.players[side].gain_money(worth)
        self.players[side].time_until_wave = WAVE_INTERVAL
        units = generate_units(power)
        angle = random.random() * 2 * math.pi
        distance = 1000 * self.players[side].ai_wave ** .2
        x = int(self.players[side].TownHall.x + distance * math.cos(angle))
        y = int(self.players[side].TownHall.y + distance * math.sin(angle))
        args = [self.object_ID, side, x, y, units[0], self.ticks, worth, str(units[1])]
        wave = Formation(self.object_ID, [], units[0], 1 - side, self, x=x, y=y, amplifier=units[1], AI=True)
        self.object_ID += 1
        wave.attack(self.players[side].TownHall)
        self.send_both({"action": "summon_wave", "args": args})

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

    def add_building_to_chunk(self, unit, location):
        if location in self.chunks:
            self.chunks[location].buildings[unit.side].append(unit)
            return
        self.chunks[location] = chunk()
        self.chunks[location].buildings[unit.side].append(unit)

    def remove_unit_from_chunk(self, unit, location):
        self.chunks[location].units[unit.side].remove(unit)

    def remove_building_from_chunk(self, unit, location):
        self.chunks[location].buildings[unit.side].remove(unit)

    def find_building(self, ID, side, entity_type=None):
        for e in self.players[side].all_buildings:
            if e.ID == ID and (entity_type == None or e.entity_type == entity_type):
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

    def find_chunk(self, c):
        if c in self.chunks:
            return self.chunks[c]
        return None


class player:

    def __init__(self, side, game):
        self.side = side
        self.game = game
        self.walls = []
        self.units = []
        self.formations = []
        self.all_buildings = []
        self.money = 0.0
        self.TownHall = None
        self.ai_wave = 0
        self.time_until_wave = WAVE_INTERVAL
        self.unit_auras = []
        self.upgrades=[]

    def on_unit_summon(self, unit):
        for e in self.unit_auras:
            e.apply(unit)

    def tick_wave_timer(self):
        self.time_until_wave -= 1
        if self.time_until_wave == 0:
            self.game.summon_ai_wave(self.side)

    def summon_townhall(self):
        self.TownHall = TownHall(TH_DISTANCE * self.side, TH_DISTANCE * self.side, self.side, self.game)

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
        [e.tick() for e in self.all_buildings]
        [e.tick() for e in self.walls]
        [e.tick() for e in self.formations]
        for e in self.unit_auras:
            e.tick()
            if not e.exists:
                self.unit_auras.remove(e)


class chunk:
    def __init__(self):
        self.units = [[], []]
        self.buildings = [[], []]

    def is_empty(self):
        return self.units[0] == [] == self.units[1] and self.buildings[0] == [] == self.buildings[1]

    def clear_units(self):
        self.units = [[], []]


##################   ---/core---  #################
##################   ---units---  #################

class Building:
    name = "TownHall"
    entity_type = "townhall"

    def __init__(self, ID, x, y, side, game):
        self.spawning = 0
        self.ID = ID
        self.x, self.y = x, y
        self.side = side
        self.size = unit_stats[self.name]["size"]
        self.health = self.max_health = unit_stats[self.name]["health"]
        self.game = game
        self.chunks = get_chunks(x, y, self.size)
        self.exists = False
        self.game.players[side].all_buildings.append(self)
        for e in self.chunks:
            game.add_building_to_chunk(self, e)
        self.upgrades_into = []
        self.comes_from = None
        self.effects = []
        self.base_stats = unit_stats[self.name]
        self.mods_add = {e: [] for e in unit_stats[self.name].keys()}
        self.mods_multiply = {e: [] for e in unit_stats[self.name].keys()}
        self.stats = {e: (self.base_stats[e] + sum(self.mods_add[e])) * product(*self.mods_multiply[e]) for e in
                      self.base_stats.keys()}

    def take_damage(self, amount, source):
        if self.exists:
            self.health -= amount
            if self.health <= 0:
                self.die()

    def die(self):
        if not self.exists:
            return
        self.game.players[self.side].all_buildings.remove(self)
        for e in self.chunks:
            self.game.remove_building_from_chunk(self, e)
        self.exists = False

    def distance_to_point(self, x, y):
        return distance(self.x, self.y, x, y) - self.size / 2

    def towards(self, x, y):
        dx, dy = self.x - x, self.y - y
        invh = inv_h(dx, dy)
        return dx * invh, dy * invh

    def tick(self):
        if self.spawning < FPS * ACTION_DELAY:
            self.spawning += 1
        if self.spawning == FPS * ACTION_DELAY:
            self.exists = True
            self.tick = self.tick2
            if self.comes_from is not None:
                self.comes_from.die()

    def tick2(self):
        if self.exists:
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


class TownHall(Building):
    name = "TownHall"
    entity_type = "townhall"

    def __init__(self, x, y, side, game):
        super().__init__(None, x, y, side, game)
        self.exists = True

    def die(self):
        if not self.exists:
            return
        super().die()
        print("game over", self.game.ticks)
        # self.game.end(1 - self.side)

    def tick(self):
        self.shove()


class Tower(Building):
    name = "Tower"
    entity_type = "tower"

    def __init__(self, ID, x, y, side, game):
        super().__init__(ID, x, y, side, game)
        self.current_cooldown = 0
        self.target = None
        self.shooting_in_chunks = get_chunks(self.x, self.y, 2 * self.stats["reach"])
        self.upgrades_into = [Tower1, Tower2]
        self.turns_without_target = 0

    @classmethod
    def get_cost(cls, params):
        return unit_stats[cls.name]["cost"]

    def tick2(self):
        self.shove()
        if self.current_cooldown > 0:
            self.current_cooldown -= 1 / FPS
        if self.current_cooldown <= 0:
            if self.acquire_target():
                self.current_cooldown += self.stats["cd"]
                self.attack(self.target)
            else:
                self.turns_without_target += 1

    def attack(self, target):
        Arrow(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"],
              self.stats["bulletspeed"],
              self.stats["reach"] * 1.5)

    def acquire_target(self):
        if self.target is not None and self.target.exists and self.target.distance_to_point(self.x,
                                                                                            self.y) < self.stats[
            "reach"]:
            return True
        if self.turns_without_target == 60 or self.turns_without_target == 0:
            self.turns_without_target = 0
            for c in self.shooting_in_chunks:
                chonker = self.game.find_chunk(c)
                if chonker is not None:
                    for unit in chonker.units[1 - self.side]:
                        if unit.exists and unit.distance_to_point(self.x, self.y) < self.stats["reach"]:
                            self.target = unit
                            self.turns_without_target = 0
                            return True
                    for unit in chonker.buildings[1 - self.side]:
                        if unit.exists and unit.distance_to_point(self.x, self.y) < self.stats["reach"]:
                            self.target = unit
                            self.turns_without_target = 0
                            return True
            return False
        return False


class Tower1(Tower):
    name = "Tower1"

    def __init__(self, target):
        super().__init__(target.ID, target.x, target.y, target.side, target.game)
        self.comes_from = target
        self.upgrades_into = [Tower11]


class Tower11(Tower):
    name = "Tower11"

    def __init__(self, target):
        super().__init__(target.ID, target.x, target.y, target.side, target.game)
        self.comes_from = target
        self.upgrades_into = []
        self.shots = unit_stats[self.name]["shots"]
        self.spread = unit_stats[self.name]["spread"]

    def attack(self, target):
        direction = target.towards(self.x, self.y)
        rot = get_rotation_norm(*direction)
        for i in range(int(self.shots)):
            Bullet(self.x, self.y, rot + self.spread * math.sin(self.game.ticks + 5 * i), self.game, self.side,
                   self.stats["dmg"],
                   self.stats["bulletspeed"],
                   self.stats["reach"] * 1.5)


class Tower2(Tower):
    name = "Tower2"

    def __init__(self, target):
        super().__init__(target.ID, target.x, target.y, target.side, target.game)
        self.comes_from = target
        self.explosion_radius = unit_stats[self.name]["explosion_radius"]
        self.upgrades_into = [Tower21, Tower22]

    def attack(self, target):
        Boulder(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"],
                self.stats["bulletspeed"],
                target.distance_to_point(self.x, self.y), self.explosion_radius)


class Tower21(Tower):
    name = "Tower21"

    def __init__(self, target):
        super().__init__(target.ID, target.x, target.y, target.side, target.game)
        self.comes_from = target
        self.explosion_radius = unit_stats[self.name]["explosion_radius"]
        self.upgrades_into = []

    def attack(self, target):
        Meteor(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"],
               self.stats["bulletspeed"],
               target.distance_to_point(self.x, self.y), self.explosion_radius)


class Tower22(Tower):
    name = "Tower22"

    def __init__(self, target):
        super().__init__(target.ID, target.x, target.y, target.side, target.game)
        self.comes_from = target
        self.explosion_radius = unit_stats[self.name]["explosion_radius"]
        self.upgrades_into = []

    def attack(self, target):
        Egg(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"],
            self.stats["bulletspeed"],
            target.distance_to_point(self.x, self.y), self.explosion_radius)


class Farm(Building):
    name = "Farm"
    entity_type = "farm"

    def __init__(self, ID, x, y, side, game):
        super().__init__(ID, x, y, side, game)
        self.production = unit_stats[self.name]["production"]
        self.upgrades_into = [Farm1, Farm2]

    @classmethod
    def get_cost(cls, params):
        return unit_stats[cls.name]["cost"]

    def tick2(self):
        super().tick2()
        self.game.players[self.side].gain_money(self.production)


class Farm1(Farm):
    name = "Farm1"

    def __init__(self, target):
        super().__init__(target.ID, target.x, target.y, target.side, target.game)
        self.comes_from = target
        self.upgrades_into = []


class Farm2(Farm):
    name = "Farm2"

    def __init__(self, target):
        super().__init__(target.ID, target.x, target.y, target.side, target.game)
        self.comes_from = target
        self.upgrades_into = []


possible_buildings = [Tower, Farm, Tower1, Tower2, Tower21, Tower11, Farm1, Farm2, Tower22]


class Wall:
    name = "Wall"

    def __init__(self, ID, t1, t2, side, game):
        self.entity_type = "wall"
        self.exists = False
        self.spawning = 0
        self.health = unit_stats[self.name]["health"]
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
        if not self.exists:
            return
        self.game.players[self.side].walls.remove(self)
        self.game.players[self.side].all_buildings.remove(self)
        self.exists = False

    @classmethod
    def get_cost(cls, params):
        return unit_stats[cls.name]["cost"]

    def take_damage(self, amount, source):
        if not self.exists:
            return
        self.health -= amount
        if self.health <= 0:
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
        if self.spawning < FPS * ACTION_DELAY:
            self.spawning += 1
        if self.spawning == FPS * ACTION_DELAY:
            self.exists = True
            self.tick = self.tick2

    def tick2(self):
        self.shove()

    def delete(self):
        self.game.players[self.side].walls.remove(self)
        self.game.players[self.side].all_buildings.remove(self)


class Formation:
    def __init__(self, ID, instructions, troops, side, game, x=None, y=None, amplifier=1, AI=False):
        self.AI = AI
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
        if x is None:
            self.x, self.y = self.game.players[self.side].TownHall.x, self.game.players[self.side].TownHall.y
        else:
            self.x, self.y = x, y
        for column in range(UNIT_FORMATION_COLUMNS):
            for row in range(UNIT_FORMATION_ROWS):
                if troops[column][row] != -1:
                    self.game.object_ID += 1
                    self.troops.append(
                        possible_units[troops[column][row]](
                            self.game.object_ID,
                            (column - self.game.unit_formation_columns / 2) * UNIT_SIZE + self.x,
                            (row - self.game.unit_formation_rows / 2) * UNIT_SIZE + self.y,
                            side,
                            column - self.game.unit_formation_columns / 2,
                            row - self.game.unit_formation_rows / 2,
                            game, self,
                            effects=(effect_stat_mult("health", amplifier),
                                     effect_stat_mult("health", amplifier))
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
        if self.spawning < FPS * ACTION_DELAY:
            self.spawning += 1
        if self.spawning == FPS * ACTION_DELAY:
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
        for e in self.troops:
            e.target = None


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

    def __init__(self, ID, x, y, side, column, row, game, formation, effects=()):
        self.entity_type = "unit"
        self.ID = ID
        self.lifetime = 0
        self.side = side
        self.game = game
        self.formation = formation
        self.x, self.y = x, y
        self.last_x, self.last_y = x, y
        self.column, self.row = column, row
        self.game.players[self.side].units.append(self)
        self.size = unit_stats[self.name]["size"]
        self.current_cooldown = 0
        self.exists = False
        self.target = None
        self.rotation = 0
        self.desired_x, self.desired_y = x, y
        self.vx, self.vy = 1, 0
        self.reached_goal = True
        self.mass = unit_stats[self.name]["mass"]
        self.chunks = get_chunks(self.x, self.y, self.size)
        for e in self.chunks:
            self.game.add_unit_to_chunk(self, e)
        self.effects = []
        self.base_stats = unit_stats[self.name]
        self.mods_add = {e: [] for e in unit_stats[self.name].keys()}
        self.mods_multiply = {e: [] for e in unit_stats[self.name].keys()}
        self.stats = {e: (self.base_stats[e] + sum(self.mods_add[e])) * product(*self.mods_multiply[e]) for e in
                      self.base_stats.keys()}
        for e in effects:
            e.apply(self)
        self.health = self.stats["health"]

    def update_stats(self, stats=None):
        if stats is None:
            stats = self.stats.keys()
        for e in stats:
            self.stats[e] = (self.base_stats[e] + sum(self.mods_add[e])) * product(*self.mods_multiply[e])

    def distance_to_point(self, x, y):
        return distance(self.x, self.y, x, y) - self.size / 2

    def towards(self, x, y):
        dx, dy = self.x - x, self.y - y
        invh = inv_h(dx, dy)
        return dx * invh, dy * invh

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
            if d > self.stats["reach"]:
                direction = other.towards(self.x, self.y)
                self.vx = self.stats["speed"] * direction[0]
                self.vy = self.stats["speed"] * direction[1]
                self.x += self.vx
                self.y += self.vy
            elif d < self.stats["reach"] / 2:
                direction = other.towards(self.x, self.y)
                self.vx = -self.stats["speed"] * direction[0] / 2
                self.vy = -self.stats["speed"] * direction[1] / 2
                self.x += self.vx
                self.y += self.vy
            return d <= self.stats["reach"]
        else:
            dist_sq = (other.x - self.x) ** 2 + (other.y - self.y) ** 2
            if dist_sq < ((other.size + self.size) * .5 + self.stats["reach"] * .8) ** 2:
                self.rotate(self.x - other.x, self.y - other.y)
                self.vx *= .7
                self.vy *= .7
                self.x += self.vx
                self.y += self.vy
                return True
            elif dist_sq > ((other.size + self.size) * .5 + self.stats["reach"]) ** 2:
                self.rotate(other.x - self.x, other.y - self.y)
                self.x += self.vx
                self.y += self.vy
            return dist_sq < ((other.size + self.size) * .5 + self.stats["reach"]) ** 2

    def attempt_attack(self, target):
        if self.current_cooldown <= 0:
            self.current_cooldown += self.stats["cd"]
            self.attack(target)

    def attack(self, target):
        pass

    def die(self):
        if not self.exists:
            return
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
        if (not self.formation.all_targets) and (
                not self.reached_goal) and self.x == self.last_x and self.y == self.last_y:
            self.x += 10
            print("xdff")
        self.last_x, self.last_y = self.x, self.y

    def rotate(self, x, y):
        if x == 0 == y:
            return
        inv_hypot = inv_h(x, y)
        self.vx, self.vy = x * inv_hypot * self.stats["speed"], y * inv_hypot * self.stats["speed"]

    def summon_done(self):
        self.exists = True
        self.tick = self.tick2
        self.game.players[self.side].on_unit_summon(self)

    def take_knockback(self, x, y, source):
        if not self.exists:
            return
        self.x += x
        self.y += y
        if source.side != self.side:
            if source.entity_type == "unit" and source not in self.formation.all_targets:
                self.formation.attack(source.formation)
            elif source.entity_type in ["tower", "townhall", "wall",
                                        "farm"] and source not in self.formation.all_targets:
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
        if other.ID == self.ID or not other.exists:
            return
        if max(abs(other.x - self.x), abs(other.y - self.y)) < (self.size + other.size) / 2:
            dist_sq = (other.x - self.x) ** 2 + (other.y - self.y) ** 2
            if dist_sq == 0:
                dist_sq = .01
                self.x += .01
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

    def __init__(self, ID, x, y, side, column, row, game, formation, effects=()):
        super().__init__(ID, x, y, side, column, row, game, formation, effects=effects)

    def attack(self, target):
        target.take_damage(self.stats["dmg"], self)


class Archer(Unit):
    name = "Archer"

    def __init__(self, ID, x, y, side, column, row, game, formation, effects=()):
        super().__init__(ID, x, y, side, column, row, game, formation, effects=effects)

    def attack(self, target):
        Arrow(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"],
              self.stats["bulletspeed"],
              self.stats["reach"] * 1.5)


class Trebuchet(Unit):
    name = "Trebuchet"

    def __init__(self, ID, x, y, side, column, row, game, formation, effects=()):
        super().__init__(ID, x, y, side, column, row, game, formation, effects=effects)
        self.explosion_radius = unit_stats[self.name]["explosion_radius"]

    def attack(self, target):
        Boulder(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"],
                self.stats["bulletspeed"],
                target.distance_to_point(self.x, self.y), self.explosion_radius)


class Defender(Unit):
    name = "Defender"

    def __init__(self, ID, x, y, side, column, row, game, formation, effects=()):
        super().__init__(ID, x, y, side, column, row, game, formation, effects=effects)

    def attack(self, target):
        target.take_damage(self.stats["dmg"], self)


class Bear(Unit):
    name = "Bear"

    def __init__(self, ID, x, y, side, column, row, game, formation, effects=()):
        super().__init__(ID, x, y, side, column, row, game, formation, effects=effects)

    def attack(self, target):
        target.take_damage(self.stats["dmg"], self)


possible_units = [Swordsman, Archer, Trebuchet, Defender, Bear]


class Projectile:

    def __init__(self, x, y, dx, dy, game, side, damage, speed, reach):
        self.x, self.y = x, y
        rotation = get_rotation_norm(dx, dy)
        self.vx, self.vy = speed * math.cos(rotation), speed * math.sin(rotation)
        self.side = side
        self.speed = speed
        self.game = game
        self.damage = damage
        game.projectiles.append(self)
        self.reach = reach

    def tick(self):
        self.x += self.vx
        self.y += self.vy
        c = self.game.find_chunk(get_chunk(self.x, self.y))
        if c is not None:
            for unit in c.units[1 - self.side]:
                if unit.exists and (unit.x - self.x) ** 2 + (unit.y - self.y) ** 2 <= (unit.size ** 2) / 4:
                    self.collide(unit)
                    return
            for unit in c.buildings[1 - self.side]:
                if unit.exists and (unit.x - self.x) ** 2 + (unit.y - self.y) ** 2 <= (unit.size ** 2) / 4:
                    self.collide(unit)
                    return
        for wall in self.game.players[1 - self.side].walls:
            if wall.exists and wall.distance_to_point(self.x, self.y) <= 0:
                self.collide(wall)
                return
        self.reach -= self.speed
        if self.reach <= 0:
            self.delete()

    def collide(self, unit):
        unit.take_damage(self.damage, self)
        self.delete()

    def delete(self):
        self.game.projectiles.remove(self)


class Bullet(Projectile):
    def __init__(self, x, y, angle, game, side, damage, speed, reach, scale=None):
        # (dx,dy) must be normalized
        self.x, self.y = x, y
        self.vx, self.vy = speed * math.cos(angle), speed * math.sin(angle)
        self.side = side
        self.speed = speed
        self.game = game
        self.damage = damage
        game.projectiles.append(self)
        self.reach = reach


class Arrow(Projectile):
    pass


class Boulder(Projectile):

    def __init__(self, x, y, dx, dy, game, side, damage, speed, reach, radius):
        super().__init__(x, y, dx, dy, game, side, damage, speed, reach)
        self.radius = radius

    def tick(self):
        self.x += self.vx
        self.y += self.vy
        self.reach -= self.speed
        if self.reach <= 0:
            self.explode()

    def explode(self):
        AOE_damage(self.x, self.y, self.radius, self.damage, self, self.game)
        self.delete()


class Meteor(Boulder):
    pass


class Egg(Meteor):
    pass


def AOE_damage(x, y, size, amount, source, game):
    chunks_affected = get_chunks(x, y, size)
    side = source.side
    affected_things = []
    for chunk in chunks_affected:
        c = game.find_chunk(chunk)
        if c is not None:
            for unit in c.units[1 - side]:
                if unit.distance_to_point(x, y) < size and unit not in affected_things:
                    affected_things.append(unit)
            for unit in c.buildings[1 - side]:
                if unit.distance_to_point(x, y) < size and unit not in affected_things:
                    affected_things.append(unit)
    for wall in game.players[1 - side].walls:
        if wall.distance_to_point(x, y) < size and wall not in affected_things:
            affected_things.append(wall)
    for e in affected_things:
        e.take_damage(amount, source)


class effect_stat_mult:
    def __init__(self, stat, amount, duration=None):
        self.stat = stat
        self.mult = amount
        self.remaining_duration = duration
        self.target = None

    def apply(self, target):
        self.target = target
        self.target.effects.append(self)
        self.target.mods_multiply[self.stat].append(self.mult)
        self.target.update_stats([self.stat])

    def remove(self):
        self.target.effects.remove(self)
        self.target.mods_multiply[self.stat].remove(self.mult)
        self.target.update_stats(self.stat)

    def tick(self):
        if self.remaining_duration is None:
            return
        self.remaining_duration -= 1 / FPS
        if self.remaining_duration <= 0:
            self.remove()


class aura:
    def __init__(self, effect, args, duration=None):
        self.effect = effect
        self.args = args
        self.remaining_duration = duration
        self.exists = True

    def tick(self):
        if self.remaining_duration is None:
            return
        self.remaining_duration -= 1 / FPS
        if self.remaining_duration <= 0:
            self.exists = False

    def apply(self, target):
        self.effect(*self.args).apply(target)

##################  ---/units---  #################
