import time

from imports import *
from constants import *


def generate_units(money):
    original_money = money
    rows, cols = 4, 4
    units = [[-1 for _ in range(UNIT_FORMATION_ROWS)] for _ in range(UNIT_FORMATION_COLUMNS)]

    '''
    units[1][1] = 1
    money-=possible_units[1].get_cost([])["money"]
    return units, original_money / (original_money - money)
    '''

    big, medium, small, huge = [], [], [], []
    for e in possible_units:
        if e.get_cost([])["money"] > 50000:
            huge.append(e)
        elif e.get_cost([])["money"] >= 2000:
            big.append(e)
        elif e.get_cost([])["money"] <= 100:
            small.append(e)
        else:
            medium.append(e)
    for x in range(rows):
        for y in range(cols):
            if money > 1000000:
                choice = random.choice(huge)
            elif money > 10000:
                choice = random.choice(big)
            elif money > 1000:
                choice = random.choice(medium)
            elif money > 0:
                choice = random.choice(small)
            else:
                return units, original_money / (original_money - money)
            money -= choice.get_cost([])["money"]
            units[x][y] = possible_units.index(choice)
    return units, original_money / (original_money - money)


class Game:
    def __init__(self, channel1, channel2, server):
        self.chunks = {}
        self.ticks = 0
        channel1.start(self, 0)
        channel2.start(self, 1)
        self.time_start = time.time()
        self.channels = [channel1, channel2]
        self.players = [player(0, self), player(1, self)]
        for e in self.players:
            e.summon_townhall()
        self.server = server
        self.unit_formation_columns = UNIT_FORMATION_COLUMNS
        self.unit_formation_rows = UNIT_FORMATION_ROWS
        self.debug_secs, self.debug_ticks = time.time(), 0
        self.projectiles = []
        self.generate_obstacles()

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
            self.players[0].gain_mana(PASSIVE_MANA)
            self.players[1].gain_mana(PASSIVE_MANA)
            self.players[odd_tick].tick_wave_timer()
            self.players[odd_tick - 1].tick_wave_timer()

    def network(self, data, side):
        if "action" in data:
            action = data["action"]
            if action == "place_building":
                entity_type = possible_buildings[data["entity_type"]]
                if not self.players[side].has_unit(entity_type):
                    print("cheating detected! (B)")
                    return
                if not CHEATS and self.players[side].TownHall.distance_to_point(*data["xy"]) > self.players[
                    1 - side].TownHall.distance_to_point(*data["xy"]):
                    return
                close_to_friendly = False
                proximity = unit_stats[entity_type.name]["proximity"]
                for e in self.players[side].all_buildings:
                    if e.distance_to_point(*data["xy"]) < proximity:
                        close_to_friendly = True
                if not close_to_friendly:
                    return
                chonks = [self.find_chunk(e) for e in get_chunks(*data["xy"], unit_stats[entity_type.name]["size"])]
                for chonk in chonks:
                    if chonk is None:
                        continue
                    for e in chonk.buildings[1]:
                        if e.prevents_placement:
                            if e.distance_to_point(*data["xy"]) < unit_stats[entity_type.name]["size"] / 2:
                                return
                    for e in chonk.buildings[0]:
                        if e.prevents_placement:
                            if e.distance_to_point(*data["xy"]) < unit_stats[entity_type.name]["size"] / 2:
                                return
                    for e in chonk.obstacles:
                        if e.prevents_placement:
                            if distance(*data["xy"], e.x, e.y) < (unit_stats[entity_type.name]["size"] + e.size) / 2:
                                return
                if self.players[side].attempt_purchase(entity_type.get_cost([])):
                    entity_type(data["xy"][0], data["xy"][1], side, self)
                    self.send_both({"action": "place_building", "xy": data["xy"], "tick": self.ticks, "side": side,
                                    "entity_type": data["entity_type"]})
            elif action == "place_wall":
                if self.players[side].attempt_purchase(Wall.get_cost([])):
                    t1, t2 = self.find_building(data["ID1"], side, "tower"), self.find_building(data["ID2"], side,
                                                                                                "tower")
                    if (None in [t1, t2]) or t1 == t2:
                        return
                    x1, y1, x2, y2 = t1.x, t1.y, t2.x, t2.y
                    for e in self.players[0].walls:
                        if e.x1 == x1 and e.y1 == y1 and e.x2 == x2 and e.y2 == y2:
                            return
                        if e.x2 == x1 and e.y2 == y1 and e.x1 == x2 and e.y1 == y2:
                            return
                    for e in self.players[1].walls:
                        if e.x1 == x1 and e.y1 == y1 and e.x2 == x2 and e.y2 == y2:
                            return
                        if e.x2 == x1 and e.y2 == y1 and e.x1 == x2 and e.y1 == y2:
                            return
                    Wall(t1, t2, side, self)
                    self.send_both({"action": "place_wall", "tick": self.ticks, "side": side,
                                    "pos": [t1.x, t1.y, t2.x, t2.y]})
            elif action == "summon_formation":
                confirmed_units = []
                for e in data["troops"]:
                    for troop in e:
                        if troop not in confirmed_units and troop != -1:
                            if not self.players[side].has_unit(possible_units[troop]):
                                print("cheating detected! (F)")
                                return
                            else:
                                confirmed_units.append(troop)
                if self.players[side].attempt_purchase(Formation.get_cost(data["troops"])):
                    if is_empty_2d(data["troops"]):
                        return
                    Formation(data["instructions"], data["troops"], side, self)
                    self.send_both({"action": "summon_formation", "tick": self.ticks, "side": side,
                                    "instructions": data["instructions"], "troops": data["troops"]})
            elif action == "buy upgrade":
                target = self.find_building(data["building ID"], side)
                if target is None or len(target.upgrades_into) <= data["upgrade num"]:
                    return
                if not self.players[side].has_unit(target.upgrades_into[data["upgrade num"]]):
                    return
                if target is not None and target.exists and self.players[side].attempt_purchase(
                        target.upgrades_into[data["upgrade num"]].get_cost([])):
                    target.upgrades_into[data["upgrade num"]](target)
                    self.send_both({"action": "upgrade", "tick": self.ticks, "side": side, "ID": data["building ID"],
                                    "upgrade num": data["upgrade num"],
                                    "backup": [possible_buildings.index(target.upgrades_into[data["upgrade num"]]),
                                               target.x, target.y, self.ticks, side, target.ID]})
                    target.upgrades_into = []
            elif action == "ping":
                self.channels[side].Send({"action": "pong", "time": str(time.time())})
            elif action == "send_wave":
                for e in self.players[1 - side].formations:
                    if e.AI:
                        return
                self.summon_ai_wave(side)
            elif action == "th upgrade":
                upg = possible_upgrades[data["num"]]
                for e in upg.previous:
                    if not self.players[side].has_upgrade(e):
                        return
                for e in upg.excludes:
                    if FACTION_LOCK and (self.players[side].has_upgrade(e) or self.players[side].is_upgrade_pending(e)):
                        return
                if self.players[side].has_upgrade(upg) or self.players[side].is_upgrade_pending(upg):
                    return
                if self.players[side].attempt_purchase(upg.get_cost()):
                    upg(self.players[side])
                    self.send_both({"action": "th upgrade", "side": side, "tick": self.ticks, "num": data["num"]})
            elif action == "spell":
                entity_type = possible_spells[data["num"]]
                if not self.players[side].has_unit(entity_type):
                    print("cheating detected! (178)")
                    return
                if self.players[side].attempt_purchase(entity_type.get_cost()):
                    entity_type(self, side, data["x"], data["y"])
                    data["tick"] = self.ticks
                    data["side"] = side
                    self.send_both(data)

    def summon_ai_wave(self, side):
        self.players[side].ai_wave += 1
        power = 1000 * 1.7 ** self.players[side].ai_wave
        worth = power
        self.players[side].gain_money(worth)
        self.players[side].time_until_wave = WAVE_INTERVAL
        units = generate_units(power)
        angle = random.random() * 2 * math.pi
        distance = 1500 * self.players[side].ai_wave ** .2
        x = int(self.players[side].TownHall.x + distance * math.cos(angle))
        y = int(self.players[side].TownHall.y + distance * math.sin(angle))
        args = [side, x, y, units[0], self.ticks, worth, str(units[1])]
        wave = Formation([], units[0], 1 - side, self, x=x, y=y, amplifier=units[1], AI=True)
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

    def add_obstacle_to_chunk(self, unit, location):
        if location in self.chunks:
            self.chunks[location].obstacles.append(unit)
            return
        self.chunks[location] = chunk()
        self.chunks[location].obstacles.append(unit)

    def add_wall_to_chunk(self, unit, location):
        if location in self.chunks:
            self.chunks[location].walls[unit.side].append(unit)
            return
        self.chunks[location] = chunk()
        self.chunks[location].walls[unit.side].append(unit)

    def remove_wall_from_chunk(self, unit, location):
        self.chunks[location].walls[unit.side].remove(unit)

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

    def find_formation(self, ID, side):
        for e in self.players[side].formations:
            if e.ID == ID:
                return e
        return None

    def generate_obstacles(self):
        seed = random.random()
        random.seed(seed)
        for mountainrange in range(MOUNTAINRANGES):
            failsafe, x, y = 0, random.randint(-MOUNTAINSPREAD, MOUNTAINSPREAD), random.randint(-MOUNTAINSPREAD,
                                                                                                MOUNTAINSPREAD)
            while (self.players[0].TownHall.distance_to_point(x, y) < MOUNTAIN_TH_DISTANCE or
                   self.players[1].TownHall.distance_to_point(x, y) < MOUNTAIN_TH_DISTANCE) and failsafe < 100:
                x = random.randint(-MOUNTAINSPREAD, MOUNTAINSPREAD)
                y = random.randint(-MOUNTAINSPREAD, MOUNTAINSPREAD)
                failsafe += 1
            mountains = [
                Obstacle(x, y, random.randint(MOUNTAINSIZE - MOUNTAINSIZE_VAR, MOUNTAINSIZE + MOUNTAINSIZE_VAR), self)
            ]
            for i in range(MOUNTAINS - 1):
                m = random.choice(mountains)
                size = random.randint(MOUNTAINSIZE - MOUNTAINSIZE_VAR, MOUNTAINSIZE + MOUNTAINSIZE_VAR)
                angle = random.random() * 2 * math.pi
                mountains.append(
                    Obstacle(m.x + math.cos(angle) * size * .8, m.y + math.sin(angle) * size * .8, size, self))
        self.send_both({"action": "generate obstacles", "seed": str(seed)})


class player:

    def __init__(self, side, game):
        self.side = side
        self.game = game
        self.walls = []
        self.units = []
        self.formations = []
        self.all_buildings = []
        self.spells = []
        self.resources = {"money": STARTING_MONEY, "mana": STARTING_MANA}
        self.max_mana = MAX_MANA
        self.TownHall = None
        self.ai_wave = 0
        self.time_until_wave = WAVE_INTERVAL
        self.auras = []
        self.pending_upgrades = []
        self.owned_upgrades = [Upgrade_default(self)]
        self.unlocked_units = [Swordsman, Archer, Defender, Tower, Wall, Farm, Tower1, Tower2, Tower11, Tower21,
                               Farm1, Farm2, Tower3, Tower31, Farm11, Fireball, Freeze, Rage, Tower23, Tower221, Tower4,
                               Tower41, Farm21, TownHall1, Mancatcher]
        self.farm_value = 1000
        self.items = []

    def gain_mana(self, amount):
        self.resources["mana"] = min(self.resources["mana"] + amount, self.max_mana)

    def add_aura(self, aur):
        self.auras.append(aur)
        if aur.everywhere:
            [aur.apply(e) for e in self.units]
            [aur.apply(e) for e in self.all_buildings]
            [aur.apply(e) for e in self.walls]

    def has_upgrade(self, upg):
        for e in self.owned_upgrades:
            if e.__class__ == upg:
                return True
        return False

    def is_upgrade_pending(self, upg):
        for e in self.pending_upgrades:
            if e.__class__ == upg:
                return True
        return False

    def unlock_unit(self, unit):
        if self.has_unit(unit):
            return
        self.unlocked_units.append(unit)

    def has_unit(self, unit):
        return unit in self.unlocked_units

    def on_unit_summon(self, unit):
        for e in self.auras:
            if e.everywhere:
                e.apply(unit)

    def on_building_summon(self, unit):
        for e in self.auras:
            if e.everywhere:
                e.apply(unit)

    def tick_wave_timer(self):
        self.time_until_wave -= 1
        if self.time_until_wave == 0:
            self.game.summon_ai_wave(self.side)

    def summon_townhall(self):
        self.TownHall = TownHall(TH_DISTANCE * (self.side - .5), TH_DISTANCE * (self.side - .5), self.side, self.game)

    def gain_money(self, amount):
        self.resources["money"] += amount

    def gain_resource(self, amount, key):
        self.resources[key] += amount

    def attempt_purchase(self, amount):
        for key, value in amount.items():
            if self.resources[key] < value:
                return False
        for key, value in amount.items():
            self.resources[key] -= value
        return True

    def tick_units(self):
        # ticks before other stuff to ensure the units are in their chunks
        [e.tick() for e in self.units]

    def tick(self):
        [e.tick() for e in self.all_buildings]
        [e.tick() for e in self.walls]
        [e.tick() for e in self.formations]
        [e.tick() for e in self.spells]
        for e in self.auras:
            e.tick()
            if not e.exists:
                self.auras.remove(e)
        [e.upgrading_tick() for e in self.pending_upgrades]


class chunk:
    def __init__(self):
        self.units = [[], []]
        self.buildings = [[], []]
        self.walls = [[], []]
        self.obstacles = []

    def is_empty(self):
        return self.units[0] == [] == self.units[1] == self.buildings[0] == [] == self.buildings[1] == \
               self.walls[0] == self.walls[1]

    def clear_units(self):
        self.units = [[], []]


##################   ---/core---  #################
##################   ---units---  #################
class Obstacle:
    prevents_placement = False

    def __init__(self, x, y, size, game: Game):
        self.x, self.y, self.size, self.game = x, y, size, game
        chunks = get_chunks(x, y, size)
        for e in chunks:
            game.add_obstacle_to_chunk(self, e)

    def collide(self, e):
        if not e.exists or (self.x - e.x) ** 2 + (self.y - e.y) ** 2 > (e.size + self.size) ** 2 / 4:
            return
        effect_combined((effect_stat_mult, effect_stat_mult),
                        (("speed", constants.MOUNTAIN_SLOWDOWN), ("mass", 1 / constants.MOUNTAIN_SLOWDOWN)),
                        2, "mountain").apply(e)


class Building:
    name = "TownHall"
    entity_type = "townhall"
    prevents_placement = True

    def __init__(self, x, y, side, game, instant=False, size_override=None):
        x, y = int(x), int(y)
        self.spawning = 0
        self.ID = (x, y, self.name, game.ticks)
        self.x, self.y = x, y
        self.side = side
        self.size = unit_stats[self.name]["size"] if size_override is None else size_override
        self.health = unit_stats[self.name]["health"]
        self.game = game
        self.chunks = get_chunks_force_circle(x, y, self.size)
        self.exists = instant
        self.game.players[side].all_buildings.append(self)
        for e in self.chunks:
            game.add_building_to_chunk(self, e)
        self.collision_chunks = []
        for c in self.chunks:
            self.collision_chunks.append(self.game.chunks[c])
        self.upgrades_into = []
        self.comes_from = None
        self.effects = []
        self.base_stats = {e: unit_stats[self.name][e] for e in unit_stats[self.name].keys()}
        if size_override is not None:
            self.base_stats["size"] = size_override
        self.mods_add = {e: [] for e in unit_stats[self.name].keys()}
        self.mods_multiply = {e: [] for e in unit_stats[self.name].keys()}
        self.stats = {e: (self.base_stats[e] + sum(self.mods_add[e])) * product(*self.mods_multiply[e]) for e in
                      self.base_stats.keys()}
        self.frozen = 0
        self.game.players[side].on_building_summon(self)
        self.summoned = instant
        if instant:
            self.tick = self.tick2
            self.update_stats()
            self.on_summon()
            if self.comes_from is not None:
                self.comes_from.delete()

    def update_stats(self, stats=None):
        if not self.exists:
            return
        health_part = self.health / self.stats["health"]
        if stats is None:
            stats = self.stats.keys()
        for e in stats:
            self.stats[e] = (self.base_stats[e] + sum(self.mods_add[e])) * product(*self.mods_multiply[e])
        self.health = self.stats["health"] * health_part
        self.size = self.stats["size"]

    def take_damage(self, amount, source, type=None):
        if self.exists:
            if type is not None:
                if type + "_resistance" in self.stats.keys():
                    amount *= self.stats[type + "_resistance"]
            amount *= self.stats["resistance"]
            self.health -= amount
            if self.health <= 0:
                self.die()

    def die(self):
        if not self.exists:
            return
        self.on_die()
        self.delete()

    def on_die(self):
        pass

    def on_delete(self):
        pass

    def delete(self):
        if not self.exists:
            return
        self.game.players[self.side].all_buildings.remove(self)
        for e in self.chunks:
            self.game.remove_building_from_chunk(self, e)
        self.exists = False
        while self.effects:
            self.effects[0].on_death()
            self.effects[0].remove()
        self.on_delete()

    def distance_to_point(self, x, y):
        return distance(self.x, self.y, x, y) - self.size / 2

    def fast_point_dist(self, x, y):
        return abs(self.x - x) + abs(self.y - y) - self.size / 2

    def towards(self, x, y):
        dx, dy = self.x - x, self.y - y
        invh = inv_h(dx, dy)
        return dx * invh, dy * invh

    def tick(self):
        if self.spawning < FPS * ACTION_DELAY:
            self.spawning += 1
        if self.spawning >= FPS * ACTION_DELAY:
            self.exists = True
            self.tick = self.tick2
            self.update_stats()
            self.summoned = True
            self.on_summon()
            if self.comes_from is not None:
                self.comes_from.delete()

    def on_summon(self):
        pass

    def tick2(self):
        if self.exists:
            self.shove()
            [e.tick() for e in self.effects]

    def shove(self):
        for ch in self.collision_chunks:
            for e in ch.units[1 - self.side]:
                if not e.exists:
                    continue
                self.collide(e)

    def collide(self, e):
        dx = e.x - self.x
        dy = e.y - self.y
        s = (e.size + self.size) / 2
        if max(abs(dx), abs(dy)) < s:
            dist_sq = dx * dx + dy * dy
            if dist_sq < s ** 2:
                shovage = s * dist_sq ** -.5 - 1
                e.take_knockback(dx * shovage, dy * shovage, self)


class RangedBuilding(Building):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_cooldown = 0
        self.target = None
        self.shooting_in_chunks = get_chunks_spiral(self.x, self.y, 2 * self.stats["reach"])
        self.turns_without_target = 0

    def tick2(self):
        super().tick2()
        assert self.frozen >= 0
        if self.frozen == 0:
            if self.current_cooldown > 0:
                self.current_cooldown -= 1 * INV_FPS
            if self.current_cooldown <= 0:
                if self.acquire_target():
                    self.current_cooldown += self.stats["cd"]
                    self.attack(self.target)
                else:
                    self.turns_without_target += 1

    def acquire_target(self):
        if self.target is not None and \
                self.target.exists and self.target.distance_to_point(self.x, self.y) < self.stats["reach"]:
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

    def attack(self, target):
        pass


class Tree(Building):
    name = "Tree"
    entity_type = "tree"
    upgrades = []
    prevents_placement = False

    def __init__(self, x, y, side, game, size, health=None):
        size = max(.1, size)
        super().__init__(x, y, side, game, size_override=size * unit_stats[self.name]["size"])
        self.additionals = []
        self.bigness = size
        effect_stat_mult("health", size ** 2).apply(self)
        self.health_set = health

    def on_summon(self):
        if self.health_set is not None:
            self.health = self.health_set
        self.check_overlap()
        if not self.exists:
            return
        freq = 32
        self.additionals.append(
            AOE_aura(effect_instant_health, ((self.bigness ** 2) * self.stats["heal"],),
                     [self.x, self.y, self.bigness * self.stats["diameter"]],
                     self.game, self.side, None, None, freq))

    def on_delete(self):
        [e.delete() for e in self.additionals]

    def check_overlap(self):
        for c in self.chunks:
            Chunk = self.game.find_chunk(c)
            if Chunk is not None:
                for building in Chunk.buildings[self.side]:
                    if building.exists and building != self and building.entity_type == "tree" and \
                            building.distance_to_point(self.x, self.y) < self.size:
                        self.merge(building)
                        return

    def merge(self, other):
        new_x = (self.x * self.size ** 2 + other.x * other.size ** 2) / (self.size ** 2 + other.size ** 2)
        new_y = (self.y * self.size ** 2 + other.y * other.size ** 2) / (self.size ** 2 + other.size ** 2)
        new_size = hypot(self.size, other.size)
        new_health = self.health + other.health
        self.delete()
        other.delete()
        a = Tree(new_x, new_y, self.side, self.game, new_size / unit_stats[self.name]["size"], health=new_health)
        a.spawning = 50


class TownHall(Building):
    name = "TownHall"
    entity_type = "townhall"
    upgrades = []

    def __init__(self, x, y, side, game):
        super().__init__(x, y, side, game)
        self.exists = True
        self.tick = self.tick2
        self.upgrades_into = [TownHall1]

    def on_die(self):
        print("game over", self.game.ticks, self.game.players[self.side].resources)


class TownHall_upgrade(Building):
    name = "TownHall"
    upgrades = []

    def __init__(self, target):
        super().__init__(target.x, target.y, target.side, target.game)
        self.game.players[self.side].TownHall = self
        self.upgrades_into = [e for e in self.upgrades]
        self.comes_from = target

    def on_die(self):
        print("game over", self.game.ticks)

    @classmethod
    def get_cost(cls, params=()):
        resources = {"money": unit_stats[cls.name]["cost"]}
        for e in unit_stats[cls.name].keys():
            if e.startswith("cost_"):
                resources[e[5::]] = unit_stats[cls.name][e]
        return resources


class TownHall1(TownHall_upgrade, RangedBuilding):
    name = "TownHall1"
    upgrades = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_cooldown = 0
        self.target = None
        self.shooting_in_chunks = get_chunks_spiral(self.x, self.y, 2 * self.stats["reach"])
        self.turns_without_target = 0

    def attack(self, target):
        Arrow(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"], self,
              self.stats["bulletspeed"],
              self.stats["reach"] * 1.5, pierce=self.stats["pierce"], cluster=self.stats["cluster"],
              recursion=self.stats["recursion"])


class TownHall11(TownHall_upgrade):
    name = "TownHall11"
    upgrades = []

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.additionals = []

    def on_summon(self):
        freq = 8
        self.additionals.append(AOE_aura(effect_combined,
                                         ((effect_stat_mult, effect_stat_mult),
                                          (("speed", self.stats["slow"]), ("cd", 1 / self.stats["slow"])),
                                          freq, "townhall_freeze"),
                                         [self.x, self.y, self.stats["radius"]],
                                         self.game, 1 - self.side, None, frequency=freq))

    def on_delete(self):
        [e.delete() for e in self.additionals]


class TownHall12(TownHall_upgrade, RangedBuilding):
    name = "TownHall12"
    upgrades = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_cooldown = 0
        self.target = None
        self.shooting_in_chunks = get_chunks_spiral(self.x, self.y, 2 * self.stats["reach"])
        self.turns_without_target = 0

    def tick2(self):
        super().tick2()
        assert self.frozen >= 0
        if self.frozen == 0:
            if self.current_cooldown > 0:
                self.current_cooldown -= 1 * INV_FPS
            if self.current_cooldown <= 0:
                if self.acquire_target():
                    self.current_cooldown += self.stats["cd"]
                    self.attack(self.target)
                else:
                    self.turns_without_target += 1

    def attack(self, target):
        flame_wave(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"], self,
                   self.stats["bulletspeed"],
                   self.stats["reach"] * 1.5, self.stats["bullet_size"], pierce=self.stats["pierce"],
                   cluster=self.stats["cluster"],
                   recursion=self.stats["recursion"])


class TownHall13(TownHall_upgrade):
    upgrades = []
    name = "TownHall13"

    def on_summon(self):
        for i in range(int(self.stats["trees"])):
            size = self.stats["tree_size"] * (math.sin(self.game.ticks ** i) + 1)
            dist = self.stats["spread"] * abs(math.sin(self.game.ticks * 2 ** i))
            Tree(self.x + math.cos(self.game.ticks * 3 ** i) * dist, self.y + math.sin(self.game.ticks * 3 ** i) * dist,
                 self.side, self.game, size)


class TownHall14(TownHall_upgrade):
    upgrades = []
    name = "TownHall14"


class Tower(RangedBuilding):
    name = "Tower"
    entity_type = "tower"
    upgrades = []

    def __init__(self, x, y, side, game):
        super().__init__(x, y, side, game)
        self.upgrades_into = [e for e in self.upgrades]

    @classmethod
    def get_cost(cls, params=()):
        resources = {"money": unit_stats[cls.name]["cost"]}
        for e in unit_stats[cls.name].keys():
            if e.startswith("cost_"):
                resources[e[5::]] = unit_stats[cls.name][e]
        return resources

    def attack(self, target):
        Arrow(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"], self,
              self.stats["bulletspeed"],
              self.stats["reach"] * 1.5, pierce=self.stats["pierce"], cluster=self.stats["cluster"],
              recursion=self.stats["recursion"])


class Tower_upgrade(Tower):
    name = "Tower1"
    upgrades = []

    def __init__(self, target):
        super().__init__(target.x, target.y, target.side, target.game)
        self.comes_from = target
        self.ID = target.ID


class Tower1(Tower_upgrade):
    name = "Tower1"
    upgrades = []


class Tower4(Tower_upgrade):
    name = "Tower4"
    upgrades = []


class Tower41(Tower_upgrade):
    name = "Tower41"
    upgrades = []


class Tower11(Tower_upgrade):
    name = "Tower11"
    upgrades = []

    def attack(self, target):
        direction = target.towards(self.x, self.y)
        rot = get_rotation_norm(*direction)
        for i in range(int(self.stats["shots"])):
            Bullet(self.x, self.y, rot + self.stats["spread"] * math.sin(self.game.ticks + 5 * i), self.game, self.side,
                   self.stats["dmg"], self,
                   self.stats["bulletspeed"],
                   self.stats["reach"] * 1.5)


class Tower2(Tower_upgrade):
    name = "Tower2"
    upgrades = []

    def attack(self, target):
        Boulder(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"], self,
                self.stats["bulletspeed"],
                target.distance_to_point(self.x, self.y), self.stats["explosion_radius"], pierce=self.stats["pierce"],
                cluster=self.stats["cluster"], recursion=self.stats["recursion"])


class Tower23(Tower_upgrade):
    name = "Tower23"
    upgrades = []

    def attack(self, target):
        AOE_damage(self.x, self.y, self.stats["reach"], self.stats["dmg"], self, self.game)


class Tower231(Tower_upgrade):
    name = "Tower231"
    upgrades = []

    def attack(self, target):
        AOE_damage(self.x, self.y, self.stats["flame_radius"], self.stats["dmg2"], self, self.game)
        direction = target.towards(self.x, self.y)
        flame_wave(self.x, self.y, *direction, self.game, self.side, self.stats["dmg"], self, self.stats["bulletspeed"],
                   self.stats["reach"] * 1.2, self.stats["bullet_size"],
                   pierce=self.stats["pierce"], cluster=self.stats["cluster"], recursion=self.stats["recursion"])


class Tower22(Tower_upgrade):
    name = "Tower22"
    upgrades = []

    def attack(self, target):
        if target is None:
            angle = self.game.ticks ** 2
            dist = self.stats["reach"] * abs(math.sin(self.game.ticks))
            dx = dist * math.cos(angle)
            dy = dist * math.sin(angle)
        else:
            dx, dy = target.x - self.x, target.y - self.y
        Mine(self.x, self.y, dx, dy, self.game, self.side, self.stats["dmg"], self,
             self.stats["bulletspeed"],
             hypot(dx, dy), self.stats["explosion_radius"], self.stats["duration"],
             pierce=self.stats["pierce"],
             cluster=self.stats["cluster"], recursion=self.stats["recursion"])

    def tick2(self):
        super().tick2()
        if self.current_cooldown > 0:
            self.current_cooldown -= 1 * INV_FPS
        if self.current_cooldown <= 0:
            self.current_cooldown += self.stats["cd"]
            if self.acquire_target():
                self.attack(self.target)
            else:
                self.turns_without_target += 1
                self.attack(None)

    def acquire_target(self):
        if self.target is not None and \
                self.target.exists and self.target.distance_to_point(self.x, self.y) < self.stats["reach"]:
            return True
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


class Tower221(Tower_upgrade):
    name = "Tower221"
    upgrades = []

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.t_stats = {}
        for k, v in self.stats.items():
            if k.startswith("t_"):
                self.t_stats[k[2::]] = v

    def attack(self, target):
        angle = self.game.ticks ** 2
        dist = self.stats["reach"] * abs(math.sin(self.game.ticks))
        dx = dist * math.cos(angle)
        dy = dist * math.sin(angle)
        Turret(self.x + dx, self.y + dy, self.t_stats, self.stats["spawn_lifetime"], self.side, self.game)

    def tick2(self):
        super().tick2()
        if self.current_cooldown > 0:
            self.current_cooldown -= 1 * INV_FPS
        if self.current_cooldown <= 0:
            self.current_cooldown += self.stats["cd"]
            self.attack(None)


class Turret(RangedBuilding):
    name = "Turret"
    entity_type = "tower"
    upgrades = []
    prevents_placement = False

    def __init__(self, x, y, stats, lifetime, side, game, alt_attack=None):
        if "size" in stats:
            super().__init__(x, y, side, game, instant=True, size_override=stats["size"])
        else:
            super().__init__(x, y, side, game, instant=True)
        self.upgrades_into = []
        for s in stats:
            self.base_stats[s] = stats[s]
        self.lifetime = lifetime
        self.update_stats()
        self.shooting_in_chunks = get_chunks_spiral(self.x, self.y, 2 * self.stats["reach"])
        if alt_attack is not None:
            self.attack = alt_attack

    def tick2(self):
        super().tick2()
        self.lifetime -= INV_FPS
        if self.lifetime <= 0:
            self.delete()

    def attack(self, target):
        Bullet(self.x, self.y, get_rotation_norm(*target.towards(self.x, self.y)), self.game, self.side,
               self.stats["dmg"], self,
               self.stats["bulletspeed"],
               self.stats["reach"] * 1.5, pierce=self.stats["pierce"], cluster=self.stats["cluster"],
               recursion=self.stats["recursion"])


class Tower21(Tower_upgrade):
    name = "Tower21"
    upgrades = []

    def attack(self, target):
        Meteor(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"], self,
               self.stats["bulletspeed"],
               target.distance_to_point(self.x, self.y), self.stats["explosion_radius"], pierce=self.stats["pierce"],
               cluster=self.stats["cluster"], recursion=self.stats["recursion"])


class Tower211(Tower_upgrade):
    name = "Tower211"
    upgrades = []

    def attack(self, target):
        Egg(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"], self,
            self.stats["bulletspeed"],
            target.distance_to_point(self.x, self.y), self.stats["explosion_radius"], pierce=self.stats["pierce"],
            cluster=self.stats["cluster"], recursion=self.stats["recursion"])


class Tower3(Tower_upgrade):
    name = "Tower3"
    upgrades = []

    def attack(self, target):
        Arrow(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"], self,
              self.stats["bulletspeed"],
              self.stats["reach"], pierce=self.stats["pierce"], cluster=self.stats["cluster"],
              recursion=self.stats["recursion"])


class Tower31(Tower_upgrade):
    name = "Tower31"
    upgrades = []

    def attack(self, target):
        Arrow(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"], self,
              self.stats["bulletspeed"],
              self.stats["reach"], pierce=self.stats["pierce"], cluster=self.stats["cluster"],
              recursion=self.stats["recursion"])


class Farm(Building):
    name = "Farm"
    entity_type = "farm"
    upgrades = []

    def __init__(self, x, y, side, game):
        super().__init__(x, y, side, game)
        self.upgrades_into = [e for e in self.upgrades]

    @classmethod
    def get_cost(cls, params=()):
        resources = {"money": unit_stats[cls.name]["cost"]}
        for e in unit_stats[cls.name].keys():
            if e.startswith("cost_"):
                resources[e[5::]] = unit_stats[cls.name][e]
        return resources

    def tick2(self):
        super().tick2()
        assert self.frozen >= 0
        if self.frozen == 0:
            self.game.players[self.side].gain_money(self.stats["production"])


class Farm_upgrade(Farm):
    name = "Tower1"
    upgrades = []

    def __init__(self, target):
        super().__init__(target.x, target.y, target.side, target.game)
        self.comes_from = target
        self.ID = target.ID


class Farm1(Farm_upgrade):
    name = "Farm1"
    upgrades = []


class Farm11(Farm_upgrade):
    name = "Farm11"
    upgrades = []


class Farm2(Farm_upgrade):
    name = "Farm2"
    upgrades = []


class Farm21(Farm_upgrade):
    name = "Farm21"
    upgrades = []

    def __init__(self, target):
        super().__init__(target)
        self.additionals = []

    def on_summon(self):
        self.additionals.append(
            aura(effect_combined,
                 (
                     (effect_stat_mult, effect_stat_mult, effect_stat_add),
                     (("speed", self.stats["buff"]),
                      ("dmg", self.stats["buff"]),
                      ("health", self.stats["health_buff"])),
                     None, self.ID
                 ),
                 self.game, self.side, None, ["unit"]))

    def on_delete(self):
        [e.delete() for e in self.additionals]


possible_buildings = [Tower, Farm, Tower1, Tower2, Tower21, Tower11, Farm1, Farm2, Tower211, Tower3, Tower31, Tower22,
                      Tower221, Tower4, Tower41, Farm21,
                      Farm11, Tower23, Tower231, TownHall, TownHall11, TownHall12, TownHall13, TownHall14, TownHall1]


def get_upg_num(cls):
    return int(cls.__name__[-1])


for dddd in possible_buildings:
    name1 = dddd.__name__
    for j in possible_buildings:
        name2 = j.__name__
        if len(name1) == len(name2) + 1 and name1[0:-1] == name2:
            j.upgrades.append(dddd)
            j.upgrades.sort(key=get_upg_num)
            continue


class Wall:
    name = "Wall"
    entity_type = "wall"
    prevents_placement = True

    def __init__(self, t1, t2, side, game):
        self.exists = False
        self.spawning = 0
        self.health = unit_stats[self.name]["health"]
        self.width = unit_stats[self.name]["size"]
        self.ID = (t1.x, t1.y, game.ticks)
        self.x1, self.y1, self.x2, self.y2 = t1.x, t1.y, t2.x, t2.y
        self.x, self.y = (self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2
        self.length = ((self.x1 - self.x2) ** 2 + (self.y1 - self.y2) ** 2) ** .5
        self.norm_vector = ((self.y2 - self.y1) / self.length, (self.x1 - self.x2) / self.length)
        self.line_c = -self.norm_vector[0] * self.x1 - self.norm_vector[1] * self.y1
        self.crossline_c = (-self.norm_vector[1] * (self.x1 + self.x2) + self.norm_vector[0] * (self.y1 + self.y2)) * .5
        self.side = side
        self.game = game
        game.players[side].walls.append(self)

        self.chunks = get_wall_chunks(self.x1, self.y1, self.x2, self.y2, self.norm_vector, self.line_c, self.width)
        for e in self.chunks:
            self.game.add_wall_to_chunk(self, e)
        self.collision_chunks = []
        for c in self.chunks:
            self.collision_chunks.append(self.game.chunks[c])

        self.effects = []
        self.base_stats = unit_stats[self.name]
        self.mods_add = {e: [] for e in unit_stats[self.name].keys()}
        self.mods_multiply = {e: [] for e in unit_stats[self.name].keys()}
        self.stats = {e: (self.base_stats[e] + sum(self.mods_add[e])) * product(*self.mods_multiply[e]) for e in
                      self.base_stats.keys()}
        self.frozen = 0
        game.players[side].on_building_summon(self)

    def die(self):
        if not self.exists:
            return
        self.game.players[self.side].walls.remove(self)
        [self.game.remove_wall_from_chunk(self, e) for e in self.chunks]
        self.exists = False
        while self.effects:
            self.effects[0].on_death()
            self.effects[0].remove()

    def update_stats(self, stats=None):
        if not self.exists:
            return
        health_part = self.health / self.stats["health"]
        if stats is None:
            stats = self.stats.keys()
        for e in stats:
            self.stats[e] = (self.base_stats[e] + sum(self.mods_add[e])) * product(*self.mods_multiply[e])
        self.health = self.stats["health"] * health_part
        self.width = self.stats["size"]

    @classmethod
    def get_cost(cls, params=()):
        resources = {"money": unit_stats[cls.name]["cost"]}
        for e in unit_stats[cls.name].keys():
            if e.startswith("cost_"):
                resources[e[5::]] = unit_stats[cls.name][e]
        return resources

    def take_damage(self, amount, source, type=None):
        if not self.exists:
            return
        if type is not None:
            if type + "_resistance" in self.stats.keys():
                amount *= self.stats[type + "_resistance"]
        self.health -= amount * self.stats["resistance"]
        if self.health <= 0:
            self.die()
            return

    def shove(self):
        for ch in self.collision_chunks:
            for e in ch.units[1 - self.side]:
                if not e.exists:
                    return
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
        if (x - self.x1) ** 2 + (y - self.y1) ** 2 < (x - self.x2) ** 2 + (
                y - self.y2) ** 2:
            invh = inv_h(self.x1 - x, self.y1 - y)
            return (self.x1 - x) * invh, (self.y1 - y) * invh
        invh = inv_h(self.x2 - x, self.y2 - y)
        return (self.x2 - x) * invh, (self.y2 - y) * invh

    def distance_to_point(self, x, y):
        if point_line_dist(x, y, (self.norm_vector[1], -self.norm_vector[0]), self.crossline_c) < self.length * .5:
            return point_line_dist(x, y, self.norm_vector, self.line_c) - self.width / 2
        if (x - self.x1) ** 2 + (y - self.y1) ** 2 < (x - self.x2) ** 2 + (
                y - self.y2) ** 2:
            return distance(x, y, self.x1, self.y1) - self.width / 2
        return distance(x, y, self.x2, self.y2) - self.width / 2

    def fast_point_dist(self, x, y):
        return self.distance_to_point(x, y)

    def tick(self):
        if self.spawning < FPS * ACTION_DELAY:
            self.spawning += 1
        if self.spawning >= FPS * ACTION_DELAY:
            self.exists = True
            self.tick = self.tick2
            self.update_stats()

    def tick2(self):
        self.shove()
        [e.tick() for e in self.effects]


class Formation:
    def __init__(self, instructions, troops, side, game, x=None, y=None, amplifier=1.0, AI=False):
        self.AI = AI
        self.spawning = 0
        self.ID = (game.ticks - self.spawning,)
        self.entity_type = "formation"
        self.exists = False
        self.instructions = instructions
        self.side = side
        self.game = game
        self.troops = []
        self.game.players[self.side].formations.append(self)
        if x is None:
            self.x, self.y = self.game.players[self.side].TownHall.x, self.game.players[self.side].TownHall.y
        else:
            self.x, self.y = x, y
        for column in range(UNIT_FORMATION_COLUMNS):
            for row in range(UNIT_FORMATION_ROWS):
                if troops[column][row] != -1:
                    self.troops.append(
                        possible_units[troops[column][row]](
                            self.ID + (column, row),
                            (column - self.game.unit_formation_columns / 2) * UNIT_SIZE + self.x,
                            (row - self.game.unit_formation_rows / 2) * UNIT_SIZE + self.y,
                            side,
                            column - self.game.unit_formation_columns / 2,
                            row - self.game.unit_formation_rows / 2,
                            game, self,
                            effects=() if amplifier == 1.0 else (effect_stat_mult("health", amplifier),
                                                                 effect_stat_mult("dmg", amplifier))
                        )
                    )
        self.instr_object = instruction_moving(self, self.x, self.y)
        self.all_targets = []

    @classmethod
    def get_cost(cls, params):
        cost = {"money": 0}
        for column in range(UNIT_FORMATION_COLUMNS):
            for row in range(UNIT_FORMATION_ROWS):
                if params[column][row] != -1:
                    for key, value in possible_units[params[column][row]].get_cost([]).items():
                        if key in cost:
                            cost[key] += value
                        else:
                            cost[key] = value
        return cost

    def tick(self):
        if self.spawning < FPS * ACTION_DELAY:
            self.spawning += 1
        if self.spawning >= FPS * ACTION_DELAY:
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
                elif instruction[0] == "attack":
                    target = self.game.find_building(instruction[1], 1 - self.side)
                    if target is not None and target.entity_type != "wall":
                        self.attack(target)
                        self.x = target.x
                        self.y = target.y
                    else:
                        target = self.game.find_wall(instruction[1], 1 - self.side)
                        if target is not None:
                            self.attack(target)
                            self.x = (target.x1 + target.x2) / 2
                            self.y = (target.y1 + target.y2) / 2
                        else:
                            target = self.game.find_formation(instruction[1], 1 - self.side)
                            if target is not None:
                                self.attack(target)
                                self.x = target.x
                                self.y = target.y
            else:
                if self.game.players[1 - self.side].TownHall.exists:
                    self.attack(self.game.players[1 - self.side].TownHall)
                return
        self.instr_object.tick()

    def delete(self):
        self.game.players[self.side].formations.remove(self)
        self.instr_object.target = None
        self.instr_object = None

    def attack(self, enemy):
        if enemy.entity_type == "formation":
            enemy = enemy.troops
        elif enemy.entity_type == "unit":
            if enemy in self.all_targets:
                return
            enemy = enemy.formation.troops
        else:
            enemy = [enemy, ]
        for e in enemy:
            if e not in self.all_targets:
                self.all_targets.append(e)
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
        if False not in [e.reached_goal or not e.wait_for_this for e in self.target.troops]:
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
        if False not in [e.reached_goal or not e.wait_for_this for e in self.target.troops]:
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
    retreats = True

    def __init__(self, ID, x, y, side, column, row, game, formation, effects=()):
        self.entity_type = "unit"
        self.ID = ID
        self.lifetime = 0
        self.side = side
        self.wait_for_this = True
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
        self.health = self.stats["health"]
        self.frozen = 0
        for e in effects:
            e.apply(self)

    def update_stats(self, stats=None):
        if not self.exists:
            return
        health_part = self.health / self.stats["health"]
        if stats is None:
            stats = self.stats.keys()
        for e in stats:
            self.stats[e] = (self.base_stats[e] + sum(self.mods_add[e])) * product(*self.mods_multiply[e])
        self.stats["speed"] = min(max(self.stats["speed"], 0), 100)
        self.health = self.stats["health"] * health_part
        self.size = self.stats["size"]

    def distance_to_point(self, x, y):
        return distance(self.x, self.y, x, y) - self.size / 2

    def fast_point_dist(self, x, y):
        return abs(self.x - x) + abs(self.y - y) - self.size / 2

    def towards(self, x, y):
        dx, dy = self.x - x, self.y - y
        invh = inv_h(dx, dy)
        return dx * invh, dy * invh

    @classmethod
    def get_cost(cls, params=()):
        resources = {"money": unit_stats[cls.name]["cost"]}
        for e in unit_stats[cls.name].keys():
            if e.startswith("cost_"):
                resources[e[5::]] = unit_stats[cls.name][e]
        return resources

    def take_damage(self, amount, source, type=None):
        if not self.exists:
            return
        if type is not None:
            if type + "_resistance" in self.stats.keys():
                amount *= self.stats[type + "_resistance"]
        self.health -= amount * self.stats["resistance"]
        if source is not None and source.entity_type in ["unit", "tower"] and source.exists:
            self.formation.attack(source)
        if self.health <= 0:
            self.die()
            return

    def acquire_target(self):
        if self.target is not None and self.target.exists:
            return
        self.target = None
        dist = 100000000
        for e in self.formation.all_targets:
            if e.exists:
                new_dist = e.fast_point_dist(self.x, self.y)
                if new_dist < dist:
                    dist = new_dist
                    self.target = e

    def move_in_range(self, other):
        if other.entity_type == "wall":
            d = other.distance_to_point(self.x, self.y)
            if d > self.stats["reach"] or not self.retreats:
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
            return d <= self.stats["reach"] + self.size
        else:
            dist_sq = (other.x - self.x) ** 2 + (other.y - self.y) ** 2
            if self.retreats and dist_sq < ((other.size + self.size) * .5 + self.stats["reach"] * .8) ** 2:
                self.rotate(self.x - other.x, self.y - other.y)
                self.vx *= .7
                self.vy *= .7
                self.x += self.vx
                self.y += self.vy
                return True
            elif (not self.retreats) or dist_sq > ((other.size + self.size) * .5 + self.stats["reach"]) ** 2:
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
        if not self.formation.troops:
            self.formation.delete()
        self.formation = None
        while self.effects:
            self.effects[0].on_death()
            self.effects[0].remove()

    def tick(self):
        if not self.exists:
            return
        if self.frozen == 0:
            if not self.formation.all_targets:
                x, y = self.x, self.y
                if not self.reached_goal:
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
                if self.target is not None and self.move_in_range(self.target):
                    self.attempt_attack(self.target)

        self.chunks = get_chunks(self.x, self.y, self.size)
        for e in self.chunks:
            self.game.add_unit_to_chunk(self, e)
        self.shove()
        self.lifetime += 1
        if self.current_cooldown > 0:
            self.current_cooldown -= 1 * INV_FPS
        if (not self.formation.all_targets) and (
                not self.reached_goal) and self.x == self.last_x and self.y == self.last_y:
            self.reached_goal = True
            print("xdff")
        self.last_x, self.last_y = self.x, self.y
        [e.tick() for e in self.effects]

    def rotate(self, x, y):
        if x == 0 == y:
            return
        inv_hypot = inv_h(x, y)
        self.vx, self.vy = x * inv_hypot * self.stats["speed"], y * inv_hypot * self.stats["speed"]

    def summon_done(self):
        self.exists = True
        self.game.players[self.side].on_unit_summon(self)
        self.update_stats()

    def take_knockback(self, x, y, source):
        if not self.exists:
            return
        self.x += x
        self.y += y
        if hasattr(source, "side") and source.side != self.side:
            if source.entity_type == "unit" and source not in self.formation.all_targets:
                self.formation.attack(source.formation)
            elif source.entity_type in ["tower", "townhall", "wall",
                                        "farm", "tree"] and source not in self.formation.all_targets:
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
            chonk = self.game.chunks[c]
            for e in chonk.obstacles:
                e.collide(self)
            units = chonk.units
            for e in units[self.side]:
                self.check_collision(e)
            for e in units[self.side - 1]:
                self.check_collision(e)

    def check_collision(self, other):
        if other.ID == self.ID or not other.exists:
            return
        dx = other.x - self.x
        dy = other.y - self.y
        size = (self.size + other.size) / 2
        if abs(dx) < size > abs(dy):
            dist_sq = dx * dx + dy * dy
            if dist_sq == 0:
                dist_sq = .01
            if dist_sq < size * size:
                shovage = size * dist_sq ** -.5 - 1  # desired dist / current dist -1
                mass_ratio = self.stats["mass"] / (self.stats["mass"] + other.stats["mass"])
                other.take_knockback(dx * shovage * mass_ratio, dy * shovage * mass_ratio,
                                     self)
                self.take_knockback(dx * shovage * (mass_ratio - 1),
                                    dy * shovage * (mass_ratio - 1),
                                    other)


class Swordsman(Unit):
    name = "Swordsman"

    def attack(self, target):
        target.take_damage(self.stats["dmg"], self)


class Archer(Unit):
    name = "Archer"

    def attack(self, target):
        Arrow(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"], self,
              self.stats["bulletspeed"],
              self.stats["reach"] * 1.5, pierce=self.stats["pierce"], cluster=self.stats["cluster"],
              recursion=self.stats["recursion"])


class Trebuchet(Unit):
    name = "Trebuchet"

    def attack(self, target):
        Boulder(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"], self,
                self.stats["bulletspeed"],
                max(self.stats["min_range"], target.distance_to_point(self.x, self.y)), self.stats["explosion_radius"],
                pierce=self.stats["pierce"],
                cluster=self.stats["cluster"], recursion=self.stats["recursion"])


class Defender(Unit):
    name = "Defender"

    def attack(self, target):
        target.take_damage(self.stats["dmg"], self)


class Mancatcher(Unit):
    name = "Mancatcher"

    def attack(self, target):
        if has_tag(target.name, "unit"):
            if not has_tag(target.name, "unplayable"):
                effect_catch_man(self.stats["steal"],
                                 self.stats["cd"] * self.stats["duration"] * FPS, "mancatcher").apply(target)
            effect_stat_add("speed", -self.stats["slow"] * self.mass / target.mass,
                            self.stats["cd"] * self.stats["duration"] * FPS, self.ID).apply(target)
        target.take_damage(self.stats["dmg"], self)


class Bear(Unit):
    name = "Bear"

    def attack(self, target):
        target.take_damage(self.stats["dmg"], self)


class Necromancer(Unit):
    name = "Necromancer"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.zombies = 0

    def attack(self, target):
        target.take_damage(self.stats["dmg"], self)
        if target.entity_type == "unit" and not target.exists:
            self.summon(target)

    def summon(self, e):
        if e.name == "Zombie":
            return
        a = Zombie([self.ID, self.zombies], e.x, e.y, self.side, self.column, self.row, self.game, self.formation,
                   effects=(effect_stat_add("health", e.base_stats["health"] * self.stats["steal"]),
                            effect_stat_add("dmg", e.base_stats["dmg"] * self.stats["steal"]),
                            effect_stat_add("size", e.base_stats["size"] - 19),
                            effect_stat_add("cd", e.base_stats["cd"] / self.stats["steal"])
                            )
                   )
        a.summon_done()
        self.formation.troops.append(a)
        self.zombies += 1


class Zombie(Unit):
    name = "Zombie"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.zombies = 0
        self.wait_for_this = False

    def attack(self, target):
        target.take_damage(self.stats["dmg"], self)
        if target.entity_type == "unit" and not target.exists:
            self.summon(target)

    def summon(self, e):
        if e.name == "Zombie":
            return
        a = Zombie([self.ID, self.zombies], e.x, e.y, self.side, self.column, self.row, self.game, self.formation,
                   effects=(effect_stat_add("health", e.base_stats["health"] * self.stats["steal"]),
                            effect_stat_add("dmg", e.base_stats["dmg"] * self.stats["steal"]),
                            effect_stat_add("size", e.base_stats["size"] - 19),
                            effect_stat_add("cd", e.base_stats["cd"] / self.stats["steal"])
                            )
                   )
        a.summon_done()
        self.formation.troops.append(a)
        self.zombies += 1


class Golem(Unit):
    name = "Golem"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.eaten_tower = 0

    def attack(self, target):
        if target.entity_type == "tower" and target.health > self.eaten_tower:
            self.eaten_tower = target.health
            target.die()
            return
        elif target.entity_type == "wall":
            target.take_damage(self.stats["wall_mult"] * (self.stats["dmg"] + self.eaten_tower), self)
        else:
            target.take_damage(self.stats["dmg"] + self.eaten_tower, self)

class Crab(Unit):
    name = "Crab"
    retreats = False

    def attack(self, target):
        AOE_damage(self.x, self.y, self.stats["AOE"], self.stats["dmg"], self, self.game)

possible_units = [Swordsman, Archer, Trebuchet, Defender, Bear, Necromancer, Zombie, Golem, Mancatcher, Crab]


class Projectile:

    def __init__(self, x, y, dx, dy, game, side, damage, source, speed, reach, pierce=2, cluster=5, rotation=None,
                 recursion=2):
        self.x, self.y = x, y
        if rotation is None:
            rotation = get_rotation_norm(dx, dy)
        self.vx, self.vy = speed * math.cos(rotation), speed * math.sin(rotation)
        self.side = side
        self.speed = speed
        self.game = game
        self.damage = damage
        game.projectiles.append(self)
        self.reach = reach
        self.max_reach = reach
        self.pierce = pierce
        self.max_pierce = pierce
        self.source = source
        self.cluster = int(cluster)
        self.recursion = recursion
        self.already_hit = []

    def tick(self):
        self.x += self.vx
        self.y += self.vy
        c = self.game.find_chunk(get_chunk(self.x, self.y))
        if c is not None:
            for unit in c.units[1 - self.side]:
                if unit.exists and unit not in self.already_hit and \
                        (unit.x - self.x) ** 2 + (unit.y - self.y) ** 2 <= (unit.size ** 2) / 4:
                    self.collide(unit)
                    if self.pierce < 1:
                        return
            for unit in c.buildings[1 - self.side]:
                if unit.exists and unit not in self.already_hit and \
                        (unit.x - self.x) ** 2 + (unit.y - self.y) ** 2 <= (unit.size ** 2) / 4:
                    self.collide(unit)
                    if self.pierce < 1:
                        return
            for wall in c.walls[1 - self.side]:
                if wall.exists and wall not in self.already_hit and wall.distance_to_point(self.x, self.y) <= 0:
                    self.collide(wall)
                    if self.pierce < 1:
                        return
        self.reach -= self.speed
        if self.reach <= 0:
            self.delete()

    def collide(self, unit):
        unit.take_damage(self.damage, self.source)
        self.already_hit.append(unit)
        self.pierce -= 1
        if self.pierce < 1:
            self.delete()

    def delete(self):
        self.split()
        self.game.projectiles.remove(self)

    def split(self):
        if self.recursion > 0:
            for i in range(self.cluster):
                self.__class__(self.x, self.y, 0, 0, self.game, self.side, self.damage, self.source, self.speed,
                               self.max_reach * RECURSION_REACH,
                               pierce=self.max_pierce, cluster=self.cluster,
                               rotation=self.game.ticks + 2 * math.pi * i / self.cluster, recursion=self.recursion - 1)


class Projectile_with_size(Projectile):
    def __init__(self, x, y, dx, dy, game, side, damage, source, speed, reach, size, pierce=2, cluster=5, rotation=None,
                 recursion=2):
        super().__init__(x, y, dx, dy, game, side, damage, source, speed, reach, pierce, cluster, rotation,
                         recursion)
        self.size = size

    def tick(self):
        self.x += self.vx
        self.y += self.vy
        chonkers = get_chunks(self.x, self.y, self.size)
        for chonker in chonkers:
            c = self.game.find_chunk(chonker)
            if c is not None:
                for unit in c.units[1 - self.side]:
                    if unit.exists and unit not in self.already_hit and \
                            (unit.x - self.x) ** 2 + (unit.y - self.y) ** 2 <= ((unit.size + self.size) ** 2) / 4:
                        self.collide(unit)
                        if self.pierce < 1:
                            return
                for unit in c.buildings[1 - self.side]:
                    if unit.exists and unit not in self.already_hit and \
                            (unit.x - self.x) ** 2 + (unit.y - self.y) ** 2 <= ((unit.size + self.size) ** 2) / 4:
                        self.collide(unit)
                        if self.pierce < 1:
                            return
                for wall in c.walls[1 - self.side]:
                    if wall.exists and wall not in self.already_hit and wall.distance_to_point(self.x,
                                                                                               self.y) <= self.size:
                        self.collide(wall)
                        if self.pierce < 1:
                            return
        self.reach -= self.speed
        if self.reach <= 0:
            self.delete()


class flame_wave(Projectile_with_size):
    pass


class Bullet(Projectile):
    def __init__(self, x, y, angle, game, side, damage, source, speed, reach, scale=None, pierce=1, cluster=0,
                 rotation=None, recursion=0):
        super().__init__(x, y, 0, 0, game, side, damage, source, speed, reach, pierce, cluster, angle, recursion)


class Arrow(Projectile):
    pass


class Boulder(Projectile):

    def __init__(self, x, y, dx, dy, game, side, damage, source, speed, reach, radius, pierce=2, cluster=5,
                 rotation=None, recursion=1):
        super().__init__(x, y, dx, dy, game, side, damage, source, speed, reach, pierce, cluster, rotation, recursion)
        self.radius = radius

    def tick(self):
        self.x += self.vx
        self.y += self.vy
        self.reach -= self.speed
        if self.reach <= 0:
            self.explode()

    def explode(self):
        AOE_damage(self.x, self.y, self.radius, self.damage, self.source, self.game)
        self.delete()

    def split(self):
        if self.recursion > 0:
            for i in range(self.cluster):
                self.__class__(self.x, self.y, 0, 0, self.game, self.side, self.damage, self.source, self.speed,
                               self.max_reach * RECURSION_REACH,
                               self.radius, self.max_pierce, self.cluster,
                               self.game.ticks + 2 * math.pi * i / self.cluster, self.recursion - 1)


class Mine(Boulder):
    def __init__(self, x, y, dx, dy, game, side, damage, source, speed, reach, radius, lifetime, pierce=2,
                 cluster=5, recursion=1):
        d = inv_h(dx, dy)
        super().__init__(x, y, dx * d, dy * d, game, side, damage, source, speed, reach, radius, pierce, cluster,
                         recursion=recursion)
        self.final_x, self.final_y = x + dx, y + dy
        self.finished = False
        self.lifetime = lifetime

    def tick(self):
        if not self.finished:
            self.x += self.vx
            self.y += self.vy
            self.reach -= self.speed
            if self.reach < 0:
                self.finished = True
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.explode()
            return
        if self.lifetime % 2 == 0:
            c = self.game.find_chunk(get_chunk(self.x, self.y))
            if c is not None:
                for unit in c.units[1 - self.side]:
                    if unit.exists and unit not in self.already_hit and \
                            (unit.x - self.x) ** 2 + (unit.y - self.y) ** 2 <= (unit.size ** 2) / 4:
                        self.explode()
                        return
                for unit in c.buildings[1 - self.side]:
                    if unit.exists and unit not in self.already_hit and \
                            (unit.x - self.x) ** 2 + (unit.y - self.y) ** 2 <= (unit.size ** 2) / 4:
                        self.explode()
                        return
                for wall in c.walls[1 - self.side]:
                    if wall.exists and wall not in self.already_hit and wall.distance_to_point(self.x, self.y) <= 0:
                        self.explode()
                        return


class Meteor(Boulder):
    pass


class Egg(Meteor):
    pass


def AOE_damage(x, y, size, amount, source, game, type=None):
    side = source.side
    affected_things = AOE_get(x, y, size, 1 - side, game)

    for e in affected_things:
        e.take_damage(amount, source, type)


def AOE_get(x, y, size, side, game, chunks=None):
    chunks_affected = get_chunks(x, y, size * 2) if chunks is None else chunks
    affected_things = []
    for coord in chunks_affected:
        c = game.find_chunk(coord)
        if c is not None:
            for unit in c.units[side]:
                if unit.exists and unit.distance_to_point(x, y) < size and unit not in affected_things:
                    affected_things.append(unit)
            for unit in c.buildings[side]:
                if unit.exists and unit.distance_to_point(x, y) < size and unit not in affected_things:
                    affected_things.append(unit)
            for wall in c.walls[side]:
                if wall.exists and wall.distance_to_point(x, y) < size and wall not in affected_things:
                    affected_things.append(wall)
    return affected_things


class effect:
    def __init__(self, duration=None, ID=None, from_aura=None):
        self.remaining_duration = duration
        self.target = None
        self.ID = ID
        self.from_aura = from_aura

    def apply(self, target):
        if self.ID is not None:
            for e in target.effects:
                if e.ID == self.ID:
                    self.stack(e)
                    return False
        self.target = target
        self.target.effects.append(self)
        self.on_apply(target)
        return True

    def stack(self, existing):
        if existing.remaining_duration is None or self.remaining_duration is None:
            existing.remaining_duration = None
        else:
            existing.remaining_duration = max(existing.remaining_duration, self.remaining_duration)

    def remove(self):
        if self.target is None:
            return
        self.target.effects.remove(self)
        self.on_remove()

    def tick(self):
        self.on_tick()
        if self.from_aura is not None and not self.from_aura.exists:
            self.remove()
            return
        if self.remaining_duration is None:
            return
        self.remaining_duration -= 1
        if self.remaining_duration <= 0:
            self.remove()

    def on_apply(self, target):
        pass

    def on_remove(self):
        pass

    def on_tick(self):
        pass

    def on_death(self):
        pass


class effect_catch_man(effect):
    def __init__(self, amount, duration=None, ID=None, from_aura=None):
        super().__init__(duration, ID, from_aura)
        self.amount = amount

    def on_death(self):
        you = self.target.game.players[1 - self.target.side]
        res = self.target.__class__.get_cost()
        for [key, value] in res.items():
            you.gain_resource(value * self.amount, key)


class effect_instant_health(effect):
    def __init__(self, amount):
        super().__init__(0, None)
        self.amount = amount

    def apply(self, target):
        target.health = min(target.health + self.amount, target.stats["health"])


class effect_stat_mult(effect):
    def __init__(self, stat, amount, duration=None, ID=None, from_aura=None):
        super().__init__(duration, ID, from_aura=from_aura)
        self.stat = stat
        self.mult = amount

    def apply(self, target):
        if self.stat not in target.stats:
            return
        if super().apply(target):
            self.target.mods_multiply[self.stat].append(self.mult)
            self.target.update_stats([self.stat])

    def on_remove(self):
        self.target.mods_multiply[self.stat].remove(self.mult)
        self.target.update_stats([self.stat])


class effect_freeze(effect):
    def on_apply(self, target):
        target.frozen += 1

    def on_remove(self):
        self.target.frozen -= 1


class effect_stat_add(effect):
    def __init__(self, stat, amount, duration=None, ID=None, from_aura=None):
        super().__init__(duration, ID, from_aura)
        self.stat = stat
        self.mult = amount

    def on_apply(self, target):
        if self.stat not in target.stats:
            return
        self.target.mods_add[self.stat].append(self.mult)
        self.target.update_stats([self.stat])

    def on_remove(self):
        self.target.mods_add[self.stat].remove(self.mult)
        self.target.update_stats([self.stat])


class effect_regen(effect):
    def __init__(self, amount, duration=None, ID=None, from_aura=None):
        super().__init__(duration, ID, from_aura)
        self.strength = amount

    def on_tick(self):
        self.target.health = min(self.target.stats["health"], self.target.health + self.strength)


class effect_combined(effect):
    def __init__(self, effects, args, duration=None, ID=None, from_aura=None):
        super().__init__(duration, ID, from_aura)
        self.effects = [effects[i](*args[i]) for i in range(len(effects))]

    def on_apply(self, target):
        for e in self.effects:
            e.apply(target)

    def on_remove(self):
        for e in self.effects:
            e.remove()


class aura:
    everywhere = True

    def __init__(self, effect, args, game, side, duration=None, targets=None, require_1_tag=False):
        self.effect = effect
        self.args = args
        self.require_1_tag = require_1_tag
        self.remaining_duration = duration
        self.exists = True
        self.targets = targets
        game.players[side].add_aura(self)

    def tick(self):
        if self.remaining_duration is None:
            return
        self.remaining_duration -= 1
        if self.remaining_duration <= 0:
            self.exists = False

    def apply(self, target):
        if self.targets is None or has_tags(target.name, self.targets, self.require_1_tag):
            self.effect(*self.args, from_aura=self).apply(target)

    def delete(self):
        self.exists = False


class AOE_aura:
    everywhere = False

    def __init__(self, effect, args, x_y_rad, game: Game, side, duration=None, targets=None, frequency=1,
                 require_1_tag=False):
        self.effect = effect
        self.args = args
        self.require_1_tag = require_1_tag
        self.remaining_duration = duration
        self.apply_counter = 0
        self.exists = True
        self.targets = targets
        self.x_y_rad = x_y_rad
        self.chunks = get_chunks_force_circle(*x_y_rad)
        self.game = game
        self.side = side
        self.game.players[side].auras.append(self)
        self.frequency = frequency

    def tick(self):
        if self.apply_counter % self.frequency == 0:
            self.apply_counter = 0
            affected = AOE_get(*self.x_y_rad, self.side, self.game, self.chunks)
            for e in affected:
                self.apply(e)
        self.apply_counter += 1
        if self.remaining_duration is None:
            return
        self.remaining_duration -= 1
        if self.remaining_duration <= 0:
            self.exists = False

    def apply(self, target):
        if self.targets is None or has_tags(target.name, self.targets, self.require_1_tag):
            self.effect(*self.args).apply(target)

    def delete(self):
        self.exists = False


##################  ---/units---  #################

class Upgrade:
    previous = []
    excludes = []
    name = "This Is A Bug."

    def __init__(self, player):
        player.pending_upgrades.append(self)
        self.time_remaining = float(upgrade_stats[self.name]["time"]) * FPS
        self.player = player

    def upgrading_tick(self):
        self.time_remaining -= 1
        if self.time_remaining < 0:
            self.finished()
            return True
        return False

    def finished(self):
        self.player.pending_upgrades.remove(self)
        self.player.owned_upgrades.append(self)
        self.on_finish()

    def on_finish(self):
        pass

    @classmethod
    def get_cost(cls, params=()):
        resources = {"money": int(upgrade_stats[cls.name]["cost"])}
        for e in upgrade_stats[cls.name].keys():
            if e.startswith("cost_"):
                resources[e[5::]] = int(upgrade_stats[cls.name][e])
        return resources

    @classmethod
    def get_time(cls):
        return float(upgrade_stats[cls.name]["time"])


class Upgrade_default(Upgrade):
    previous = []
    name = "The Beginning"


class Upgrade_test_1(Upgrade):
    previous = []
    name = "Bigger Stalls"

    def on_finish(self):
        self.player.unlock_unit(Bear)


class Upgrade_catapult(Upgrade):
    previous = []
    name = "Catapults"

    def on_finish(self):
        self.player.unlock_unit(Trebuchet)


class Upgrade_bigger_arrows(Upgrade):
    previous = []
    name = "Bigger Arrows"

    def on_finish(self):
        aura(effect_stat_mult, ("dmg", float(upgrade_stats[self.name]["mod"])),
             self.player.game, self.player.side,
             targets=["arrows"])


class Upgrade_more_chestplates(Upgrade):
    name = "More Chestplates"
    previous = []

    def on_finish(self):
        aura(effect_stat_mult, ("health", float(upgrade_stats[self.name]["mod"])),
             self.player.game, self.player.side,
             targets=["footman"],
             )


class Upgrade_bigger_rocks(Upgrade):
    previous = []
    name = "Bigger Rocks"

    def on_finish(self):
        aura(effect_combined, (
            (effect_stat_mult, effect_stat_mult),
            (
                ("dmg", float(upgrade_stats[self.name]["mod_dmg"])),
                ("explosion_radius", float(upgrade_stats[self.name]["mod_rad"])),
            )
        ),
             self.player.game, self.player.side, targets=["boulders"]
             )


class Upgrade_egg(Upgrade):
    previous = []
    name = "Egg Cannon"

    def on_finish(self):
        self.player.unlock_unit(Tower211)


class Upgrade_mines(Upgrade):
    previous = []
    name = "Mines"

    def on_finish(self):
        self.player.unlock_unit(Tower22)


class Upgrade_faster_archery(Upgrade):
    previous = []
    name = "Faster Archery"

    def on_finish(self):
        aura(effect_stat_mult, ("cd", float(upgrade_stats[self.name]["mod"])),
             self.player.game, self.player.side,
             targets=["arrows"])


class Upgrade_extra_recursion(Upgrade):
    name = "Extra recursion"
    previous = []

    def on_finish(self):
        effect = effect_combined
        args1 = ("cluster", int(upgrade_stats[self.name]["mod"]))
        args2 = ("explosion_radius", int(upgrade_stats[self.name]["mod_aoe"]))
        args = ((effect_stat_add, effect_stat_add), (args1, args2))
        aura(effect, args, self.player.game, self.player.side, targets=["boulders"])


class Upgrade_vigorous_farming(Upgrade):
    previous = []
    name = "Vigorous Farming"

    def on_finish(self):
        aura(effect_stat_mult, ("production", float(upgrade_stats[self.name]["mod"])),
             self.player.game, self.player.side,
             targets=["farm"])


class Upgrade_nanobots(Upgrade):
    previous = []
    name = "Nanobots"

    def on_finish(self):
        aura(effect_regen, (float(upgrade_stats[self.name]["mod"]),),
             self.player.game, self.player.side,
             targets=["building", "wall"], require_1_tag=True)


class Upgrade_walls(Upgrade):
    previous = []
    name = "Tough Walls"

    def on_finish(self):
        aura(effect_stat_mult, ("resistance", float(upgrade_stats[self.name]["mod"])),
             self.player.game, self.player.side,
             targets=["wall"])


class Upgrade_necromancy(Upgrade):
    previous = []
    name = "Necromancy"

    def on_finish(self):
        self.player.unlock_unit(Necromancer)


class Upgrade_superior_pyrotechnics(Upgrade):
    previous = []
    name = "Superior Pyrotechnics"

    def on_finish(self):
        self.player.unlock_unit(Tower231)


class Upgrade_golem(Upgrade):
    previous = []
    name = "Golem"

    def on_finish(self):
        self.player.unlock_unit(Golem)


class Upgrade_trees(Upgrade):
    previous = []
    name = "Trees"

    def on_finish(self):
        self.player.unlock_unit(Tree_spell)


class Upgrade_nature(Upgrade):
    previous = []
    excludes = []
    name = "Nature"

    def on_finish(self):
        self.player.unlock_unit(TownHall13)


class Upgrade_fire(Upgrade):
    previous = []
    excludes = []
    name = "Fire"

    def on_finish(self):
        self.player.unlock_unit(TownHall12)


class Upgrade_frost(Upgrade):
    previous = []
    excludes = []
    name = "Frost"

    def on_finish(self):
        self.player.unlock_unit(TownHall11)


class Upgrade_tech(Upgrade):
    previous = []
    excludes = []
    name = "Tech"

    def on_finish(self):
        self.player.unlock_unit(TownHall14)


class Upgrade_crab(Upgrade):
    excludes = []
    previous = []
    name = "Crabs"

    def on_finish(self):
        self.player.unlock_unit(Crab)


for uuuu in [Upgrade_frost, Upgrade_fire, Upgrade_nature, Upgrade_tech]:
    uuuu.excludes = [Upgrade_frost, Upgrade_fire, Upgrade_nature, Upgrade_tech]
    uuuu.excludes.remove(uuuu)

possible_upgrades = [Upgrade_default, Upgrade_test_1, Upgrade_bigger_arrows, Upgrade_catapult, Upgrade_bigger_rocks,
                     Upgrade_egg, Upgrade_faster_archery, Upgrade_vigorous_farming, Upgrade_mines, Upgrade_necromancy,
                     Upgrade_nanobots, Upgrade_walls, Upgrade_superior_pyrotechnics, Upgrade_golem, Upgrade_frost,
                     Upgrade_fire, Upgrade_nature, Upgrade_tech, Upgrade_trees, Upgrade_more_chestplates,
                     Upgrade_extra_recursion, Upgrade_crab]

for uuuu in possible_upgrades:
    fromme = upgrade_stats[uuuu.name]["from"].split("&")
    for uuu2 in possible_upgrades:
        if uuu2.name in fromme:
            uuuu.previous.append(uuu2)


class Spell:
    name = "Spell"
    entity_type = "spell"

    def __init__(self, game, side, x, y):
        game.players[side].spells.append(self)
        self.spawning = 0
        self.game = game
        self.side = side
        self.x, self.y = x, y
        self.delay = unit_stats[self.name]["delay"]

    def tick(self):
        if self.spawning < self.delay:
            self.spawning += 1
        if self.spawning >= self.delay:
            self.main()
            self.game.players[self.side].spells.remove(self)

    def main(self):
        pass

    @classmethod
    def get_cost(cls, params=()):
        resources = {"mana": unit_stats[cls.name]["cost"]}
        for e in unit_stats[cls.name].keys():
            if e.startswith("cost_"):
                resources[e[5::]] = unit_stats[cls.name][e]
        return resources


class Fireball(Spell):
    name = "Fireball"

    def __init__(self, game, side, x, y):
        super().__init__(game, side, x, y)
        self.x1, self.y1 = game.players[side].TownHall.x, game.players[side].TownHall.y
        self.radius = unit_stats[self.name]["radius"]
        self.dmg = unit_stats[self.name]["dmg"]
        self.delay *= distance(self.x1, self.y1, x, y)
        self.delay = max(self.delay, ACTION_DELAY * FPS)

    def main(self):
        AOE_damage(self.x, self.y, self.radius, self.dmg, self, self.game, "spell")


class Freeze(Spell):
    name = "Freeze"

    def __init__(self, game, side, x, y):
        super().__init__(game, side, x, y)
        self.radius = unit_stats[self.name]["radius"]
        self.duration = unit_stats[self.name]["duration"]

    def main(self):
        AOE_aura(effect_freeze, (self.duration,), [self.x, self.y, self.radius], self.game, 1 - self.side, 0)


class Tree_spell(Spell):
    name = "Tree_spell"

    def __init__(self, game, side, x, y):
        super().__init__(game, side, x, y)
        self.radius = unit_stats[self.name]["radius"]
        self.trees = unit_stats[self.name]["trees"]
        self.tree_size = unit_stats[self.name]["tree_size"]

    def main(self):
        for i in range(int(self.trees)):
            size = self.tree_size * (math.sin(self.game.ticks ** i) + 1)
            dist = self.radius * abs(math.sin(self.game.ticks * 2 ** i))
            Tree(self.x + math.cos(self.game.ticks * 3 ** i) * dist, self.y + math.sin(self.game.ticks * 3 ** i) * dist,
                 self.side, self.game, size)


class Rage(Spell):
    name = "Rage"

    def __init__(self, game, side, x, y):
        super().__init__(game, side, x, y)
        self.radius = unit_stats[self.name]["radius"]
        self.duration = unit_stats[self.name]["duration"]
        self.buff = unit_stats[self.name]["buff"]

    def main(self):
        freq = 16
        AOE_aura(effect_combined, (
            (effect_stat_mult, effect_stat_mult),
            (("speed", self.buff), ("cd", 1 / self.buff)),
            freq, "rage"
        ),
                 [self.x, self.y, self.radius * 2],
                 self.game, self.side, self.duration, frequency=freq
                 )


possible_spells = [Fireball, Freeze, Rage, Tree_spell]


# SHOP #################################################################################################################

class Merchant:
    def __init__(self, x, y, game: Game, tick):
        self.tick = self.tick
        dist = MERCHANT_MAX_CENTRE_DISTANCE * ((tick % 50) / 50 - 25)
        self.x = dist
        self.y = - dist
        self.game = game
        self.menu = get_merchant_items(tick, MERCHANT_ITEM_COUNT)
        self.spawning_at_tick = tick
        self.player_resources = [{}, {}]
        self.chunks = get_chunks_force_circle(x, y, MERCHANT_RANGE)

    def tick(self):
        if self.game.ticks == self.spawning_at_tick:
            self.spawn()

    def spawn(self):
        self.tick = self.tick2

    def tick2(self):
        for side in (1, 0):
            units = AOE_get(self.x, self.y, MERCHANT_RANGE, side, self.game, self.chunks)
            for unit in units:
                unit.die()
                price = unit.__class__.get_cost()
                for resource, amount in price.items():
                    if resource in self.player_resources[unit.side].keys():
                        self.player_resources[unit.side][resource] += amount
                    else:
                        self.player_resources[unit.side][resource] = amount
