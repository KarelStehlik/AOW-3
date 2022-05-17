from imports import *
import groups
from constants import *
import images
import client_utility
import noise


class Game:

    def __init__(self, side, batch, connection, time0):
        self.camx, self.camy = 0, 0
        self.ticks = 0
        self.side, self.batch = side, batch
        self.chunks = {}
        self.players = [player(0, self), player(1, self)]
        for e in self.players:
            e.summon_townhall()
        self.connection = connection
        self.batch = batch
        self.cam_move_speed = 1500
        self.start_time = time0
        self.camx_moving, self.camy_moving = 0, 0
        self.background_texgroup = client_utility.TextureBindGroup(images.Background, layer=0)
        self.background = batch.add(
            4, pyglet.gl.GL_QUADS, self.background_texgroup,
            ("v2i", (0, 0, SCREEN_WIDTH, 0,
                     SCREEN_WIDTH, SCREEN_HEIGHT, 0, SCREEN_HEIGHT)),
            ("t2f", (0, 0, SCREEN_WIDTH / 512, 0, SCREEN_WIDTH / 512, SCREEN_HEIGHT / 512,
                     0, SCREEN_HEIGHT / 512))
        )
        self.UI_topBar = UI_top_bar(self)
        self.UI_bottomBar = UI_bottom_bar(self)
        self.UI_categories = UI_categories(self, self.UI_bottomBar)
        self.unit_formation_rows = UNIT_FORMATION_ROWS
        self.unit_formation_columns = UNIT_FORMATION_COLUMNS
        self.unit_formation = UI_formation(self)
        self.UI_toolbars = [self.UI_bottomBar, self.UI_categories, self.unit_formation, self.UI_topBar]
        self.selected = selection_none(self)
        self.last_tick, self.last_dt = 0, 0
        self.projectiles = []
        self.animations = []
        self.mousex, self.mousey = 0, 0
        self.time_difference = 0
        self.time_diffs = []
        self.ping_attempts = 10
        self.ping_time = time.perf_counter()
        connection.Send({"action": "ping"})
        self.key_press_detectors = []
        self.mouse_click_detectors = []
        self.mouse_move_detectors = []
        self.cam_update_detectors = []
        self.drawables = []
        self.upgrade_menu = None
        self.minimap = minimap(self)
        self.test = 0
        self.obstacles_vlist = obstacle_vertexlist(self)
        self.all_obstacles = []
        self.pathing_map = np.ones((int((MOUNTAINSPREAD + MOUNTAINSIZE * MOUNTAINS) / PATHING_CHUNK_SIZE),) * 2)
        p = self.bgm = pyglet.media.Player()
        p.queue(noise.bgm)
        p.play()
        p.volume = MUSIC
        p.loop=True
        self.last_clock_tick = time.perf_counter()

    def open_upgrade_menu(self):
        if self.upgrade_menu is None:
            self.upgrade_menu = Upgrade_Menu(self)
            return
        if not self.upgrade_menu.opened:
            self.upgrade_menu.open()

    def determine_time(self):
        self.time_difference = 0
        self.time_diffs = []
        self.ping_attempts = 10
        self.ping_time = time.perf_counter()
        self.connection.Send({"action": "ping"})

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

    def clear_chunks(self):
        for e in self.chunks:
            self.chunks[e].clear_units()

    def find_chunk(self, c):
        if c in self.chunks:
            return self.chunks[c]
        return None

    def select(self, sel):
        self.selected.end()
        self.selected = sel(self)

    def tick(self):
        while self.ticks < FPS * (time.time() - self.time_difference - self.start_time):
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
            if time.perf_counter() - self.last_clock_tick > .3:
                pyglet.app.platform_event_loop.step(0)
                pyglet.clock.tick()
                self.last_clock_tick = time.perf_counter()
        self.update_cam(self.last_dt)
        self.players[0].graphics_update(self.last_dt)
        self.players[1].graphics_update(self.last_dt)
        [e.graphics_update(self.last_dt) for e in self.projectiles]
        self.selected.tick()
        anim = [e for e in self.animations]
        while anim:
            anim.pop(0).tick(self.last_dt)
        [e.graphics_update(self.last_dt) for e in self.drawables]
        self.batch.draw()
        self.UI_topBar.update()
        self.last_dt = time.perf_counter() - self.last_tick
        self.last_tick = time.perf_counter()

    def network(self, data):
        if "action" in data:
            action = data["action"]
            if action == "pong":
                received = time.time()
                latency = (time.perf_counter() - self.ping_time) / 2
                self.time_diffs.append(received - float(data["time"]) - latency)
                self.ping_attempts -= 1
                if self.ping_attempts > 0:
                    self.ping_time = time.perf_counter()
                    self.connection.Send({"action": "ping"})
                else:
                    self.time_difference = average(*self.time_diffs)
            elif action == "place_building":
                possible_buildings[data["entity_type"]](data["xy"][0], data["xy"][1], data["tick"],
                                                        data["side"], self)
                return
            elif action == "place_wall":
                Wall(*data["pos"], data["tick"], data["side"], self)
                return
            elif action == "summon_formation":
                Formation(data["instructions"], data["troops"], data["tick"], data["side"], self)
                return
            elif action == "upgrade":
                tar = self.find_building(data["ID"], data["side"])
                if tar is not None:
                    tar.upgrades_into[data["upgrade num"]](tar, data["tick"])
                    tar.upgrades_into = []
                    tar.ID = -1
                else:
                    bu = data["backup"]
                    possible_buildings[bu[0]](x=bu[1], y=bu[2], tick=bu[3], side=bu[4], ID=bu[5], game=self)
            elif action == "summon_wave":
                self.summon_ai_wave(*data["args"])
            elif action == "th upgrade":
                possible_upgrades[data["num"]](self.players[data["side"]], data["tick"])
                self.players[data["side"]].force_purchase(possible_upgrades[data["num"]].get_cost())
            elif action == "spell":
                self.players[data["side"]].force_purchase(possible_spells[data["num"]].get_cost())
                possible_spells[data["num"]](self, data["side"], data["tick"], data["x"], data["y"])
            elif action == "generate obstacles":
                self.generate_obstacles(float(data["seed"]))

    def summon_ai_wave(self, side, x, y, units, tick, worth, amplifier):
        wave = Formation([], units, tick, 1 - side, self, x=x, y=y, AI=True, amplifier=float(amplifier))
        wave.attack(self.players[side].TownHall)
        self.players[side].gain_money(worth)
        if side == self.side:
            self.UI_topBar.last_wave_tick = self.ticks

    def send_wave(self):
        self.connection.Send({"action": "send_wave"})

    def mouse_move(self, x, y, dx, dy):
        [e.mouse_move(x, y) for e in self.UI_toolbars]
        [e.mouse_move(x, y) for e in self.mouse_move_detectors]
        self.selected.mouse_move(x, y)
        self.mousex, self.mousey = x, y

    def mouse_drag(self, x, y, dx, dy, button, modifiers):
        [e.mouse_drag(x, y) for e in self.UI_toolbars]
        self.selected.mouse_move(x, y)

    def key_press(self, symbol, modifiers):
        if symbol == key.A:
            self.camx_moving = max(self.camx_moving - self.cam_move_speed, -self.cam_move_speed)
        elif symbol == key.S:
            self.camy_moving = max(self.camy_moving - self.cam_move_speed, -self.cam_move_speed)
        elif symbol == key.D:
            self.camx_moving = min(self.camx_moving + self.cam_move_speed, self.cam_move_speed)
        elif symbol == key.W:
            self.camy_moving = min(self.camy_moving + self.cam_move_speed, self.cam_move_speed)
        else:
            if key.NUM_9 >= symbol >= key.NUM_1:
                if len(self.UI_bottomBar.loaded) > symbol - key.NUM_1:
                    self.select(self.UI_bottomBar.loaded[symbol - key.NUM_1])
            elif 57 >= symbol >= 49:
                if len(self.UI_bottomBar.loaded) > symbol - 49:
                    self.select(self.UI_bottomBar.loaded[symbol - 49])
            elif symbol == 65307:
                self.select(selection_none)
            elif symbol in [key.E, key.R, key.T, key.Y]:
                x, y = (self.mousex + self.camx) / SPRITE_SIZE_MULT, (self.mousey + self.camy) / SPRITE_SIZE_MULT
                for e in self.players[self.side].all_buildings:
                    if e.distance_to_point(x, y) <= 0:
                        i = [key.E, key.R, key.T, key.Y].index(symbol)
                        index = i
                        total_index = 0
                        for upg in e.upgrades_into:
                            if self.players[self.side].has_unit(upg):
                                if index == 0:
                                    break
                                index -= 1
                            total_index += 1
                        if index == 0:
                            self.connection.Send(
                                {"action": "buy upgrade", "building ID": e.ID, "upgrade num": total_index})
            elif symbol == key.U:
                self.open_upgrade_menu()

        self.selected.key_press(symbol, modifiers)
        [e.key_press(symbol, modifiers) for e in self.key_press_detectors]

    def key_release(self, symbol, modifiers):
        if symbol == key.D:
            self.camx_moving = max(self.camx_moving - self.cam_move_speed, -self.cam_move_speed)
        elif symbol == key.W:
            self.camy_moving = max(self.camy_moving - self.cam_move_speed, -self.cam_move_speed)
        elif symbol == key.A:
            self.camx_moving = min(self.camx_moving + self.cam_move_speed, self.cam_move_speed)
        elif symbol == key.S:
            self.camy_moving = min(self.camy_moving + self.cam_move_speed, self.cam_move_speed)
        [e.key_release(symbol, modifiers) for e in self.key_press_detectors]

    def mouse_press(self, x, y, button, modifiers):
        [e.mouse_click(x, y, button, modifiers) for e in self.mouse_click_detectors]
        if True in [e.mouse_click(x, y) for e in self.UI_toolbars]:
            return
        self.selected.mouse_click(x, y)
        if self.upgrade_menu is not None and self.upgrade_menu.opened:
            return
        for e in self.mouse_click_detectors:
            if isinstance(e, building_upgrade_menu):
                return
        for e in self.players[self.side].all_buildings:
            if self.selected.__class__ is not selection_wall and \
                    e.distance_to_point((x + self.camx) / SPRITE_SIZE_MULT,
                                        (y + self.camy) / SPRITE_SIZE_MULT) < 0:
                building_upgrade_menu(e.ID, self)

    def mouse_release(self, x, y, button, modifiers):
        [e.mouse_release(x, y, button, modifiers) for e in self.mouse_click_detectors]
        [e.mouse_release(x, y) for e in self.UI_toolbars]
        self.selected.mouse_release(x, y)

    def mouse_scroll(self, x, y, scroll_x, scroll_y):
        pass

    def update_cam(self, dt):
        if self.upgrade_menu is not None and self.upgrade_menu.opened:
            return
        dt = min(dt, 2)
        self.camx += self.camx_moving * dt
        self.camy += self.camy_moving * dt
        x, y = self.camx / 512, self.camy / 512
        self.background.tex_coords = (x, y, x + SCREEN_WIDTH / 512, y, x + SCREEN_WIDTH / 512,
                                      y + SCREEN_HEIGHT / 512, x, y + SCREEN_HEIGHT / 512)
        [e.update_cam(self.camx, self.camy) for e in self.players]
        [e.update_cam(self.camx, self.camy) for e in self.cam_update_detectors]
        self.selected.update_cam(self.camx, self.camy)
        self.obstacles_vlist.update_cam(self.camx, self.camy)

    def centre_cam(self):
        self.camx = self.players[self.side].TownHall.x - SCREEN_WIDTH / 2
        self.camy = self.players[self.side].TownHall.y - SCREEN_HEIGHT / 2

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

    def find_formation(self, ID, side):
        for e in self.players[side].formations:
            if e.ID == ID:
                return e
        return None

    def generate_obstacles(self, seed):
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
        self.auras = []
        self.pending_upgrades = []
        self.owned_upgrades = [Upgrade_default(self, 0)]
        self.unlocked_units = [Swordsman, Archer, Mancatcher, Defender, Tower, Wall, Farm, Tower1, Tower2, Tower11,
                               Tower21, Farm1, Farm2, Tower3, Tower31, Farm11, Fireball, Freeze, Rage, Tower23,
                               Tower221, Tower4, Tower41, Farm21, TownHall1]
        self.farm_value = 0

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

    def upgrade_time_remaining(self, upg):
        for e in self.pending_upgrades:
            if e.__class__ == upg:
                return e.time_remaining
        return None

    def unlock_unit(self, unit):
        if self.has_unit(unit):
            return
        self.unlocked_units.append(unit)
        if self.side == self.game.side:
            self.game.UI_bottomBar.load_page(self.game.UI_bottomBar.page)

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

    def summon_townhall(self):
        self.TownHall = TownHall(TH_DISTANCE * (self.side - .5), TH_DISTANCE * (self.side - .5), self.side, self.game)

    def gain_money(self, amount):
        self.resources["money"] += amount

    def attempt_purchase(self, amount):
        for key, value in amount.items():
            if self.resources[key] < value:
                return False
        for key, value in amount.items():
            self.resources[key] -= value
        return True

    def force_purchase(self, amount):
        for key, value in amount.items():
            self.resources[key] -= value
        return False

    def gain_resource(self, amount, key):
        self.resources[key] += amount

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

    def graphics_update(self, dt):
        if self.side == self.game.side:
            self.game.UI_topBar.money.text = "Gold: " + str(int(self.resources["money"]))
            self.game.UI_topBar.mana.text = "Mana: " + str(int(self.resources["mana"]))
        [e.graphics_update(dt) for e in self.units]
        [e.graphics_update(dt) for e in self.walls]
        [e.graphics_update(dt) for e in self.all_buildings]
        [e.graphics_update(dt) for e in self.spells]

    def update_cam(self, x, y):
        [e.update_cam(x, y) for e in self.units]
        [e.update_cam(x, y) for e in self.all_buildings]
        [e.update_cam(x, y) for e in self.formations]
        [e.update_cam(x, y) for e in self.walls]


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


class UI_bottom_bar(client_utility.toolbar):
    def __init__(self, game):
        super().__init__(-2, 0, SCREEN_WIDTH + 2, SCREEN_HEIGHT / 5, game.batch, layer=9)
        self.game = game
        self.page = 0
        self.loaded = []
        self.load_page(0)

    def load_page(self, n):
        self.unload_page()
        i = 0
        for e in selects_all[n]:
            if e.is_unlocked(self.game):
                self.add(self.game.select, SCREEN_WIDTH * (0.01 + 0.1 * i), SCREEN_WIDTH * 0.01,
                         SCREEN_WIDTH * 0.09, SCREEN_WIDTH * 0.09, e.img, args=(e,))
                self.loaded.append(e)
                i += 1
        self.page = n

    def unload_page(self):
        [e.delete() for e in self.buttons]
        self.buttons = []
        self.loaded = []


class UI_formation(client_utility.toolbar):

    def __init__(self, game):
        self.rows, self.columns = game.unit_formation_rows, game.unit_formation_columns
        self.dot_size = SCREEN_HEIGHT * 0.1788 / self.rows
        self.game = game
        self.dot_scale = self.dot_size / images.UnitSlot.width
        super().__init__(SCREEN_WIDTH - self.dot_size * (self.columns + 4), 0, self.dot_size * (self.columns + 4),
                         self.dot_size * (self.rows + 4) + SCREEN_HEIGHT * 0.1, game.batch,
                         image=images.UnitFormFrame, layer=10)

        self.units = [[-1 for _ in range(self.rows)] for _ in range(self.columns)]

        self.sprites = [[client_utility.sprite_with_scale(images.UnitSlot, self.dot_scale, 1, 1,
                                                          self.x + self.dot_size * (j + 2.5),
                                                          self.y + self.dot_size * (i + 2.5),
                                                          batch=game.batch, group=groups.g[self.layer + 1])
                         for i in range(self.rows)] for j in range(self.columns)]
        self.add(self.send, self.x + SCREEN_HEIGHT * 0.1, self.height - SCREEN_HEIGHT * 0.1,
                 self.width - SCREEN_HEIGHT * 0.1, SCREEN_HEIGHT * 0.1, image=images.Sendbutton)
        self.add(self.fill, self.x, self.height - SCREEN_HEIGHT * 0.1, SCREEN_HEIGHT * 0.1, SCREEN_HEIGHT * 0.1)
        self.cost_count = pyglet.text.Label(x=self.x + self.width / 2, y=5, text="Cost: 0", color=(255, 240, 0, 255),
                                            group=groups.g[self.layer + 2], batch=self.batch, anchor_x="center",
                                            anchor_y="bottom", font_size=0.01 * SCREEN_WIDTH)
        self.cost = 0

    def fill(self):
        for x in range(UNIT_FORMATION_COLUMNS):
            for y in range(UNIT_FORMATION_ROWS):
                self.set_unit(x, y, -1, update_cost=False)
        for x in range(UNIT_FORMATION_COLUMNS):
            for y in range(UNIT_FORMATION_ROWS):
                self.set_unit(x, y, self.game.selected.unit_num, update_cost=False)
        self.update_cost()

    def sucessful_click(self, x, y):
        if self.x + self.dot_size * 2 < x < self.x + self.dot_size * (2 + self.columns) and \
                self.y + self.dot_size * 2 < y < self.y + self.dot_size * (2 + self.rows):
            self.game.selected.clicked_unit_slot(int((x - (self.x + self.dot_size * 2)) // self.dot_size),
                                                 int((y - (self.y + self.dot_size * 2)) // self.dot_size))

    def mouse_click(self, x, y, button=0, modifiers=0):
        if super().mouse_click(x, y):
            self.sucessful_click(x, y)

    def mouse_drag(self, x, y, button=0, modifiers=0):
        if super().mouse_drag:
            self.sucessful_click(x, y)

    def send(self):
        self.game.select(selection_unit_formation)

    def set_unit(self, x, y, num: int, update_cost=True):
        if self.units[x][y] == num:
            return
        if num != -1:
            if self.detect_obstruction(unit_stats[possible_units[num].name]["size"], x, y):
                pass
            else:
                self.units[x][y] = num
                self.sprites[x][y].delete()
                a = possible_units[num].get_image()
                half_size = unit_stats[possible_units[num].name]["size"] / 2
                a[1] *= self.dot_size / 20
                self.sprites[x][y] = client_utility.sprite_with_scale(*a,
                                                                      self.x + self.dot_size * (x + 2.5),
                                                                      self.y + self.dot_size * (y + 2.5),
                                                                      batch=self.game.batch,
                                                                      group=groups.g[self.layer + 2])
        else:
            self.units[x][y] = num
            self.sprites[x][y].delete()
            self.sprites[x][y] = client_utility.sprite_with_scale(images.UnitSlot, self.dot_scale, 1, 1,
                                                                  self.x + self.dot_size * (x + 2.5),
                                                                  self.y + self.dot_size * (y + 2.5),
                                                                  batch=self.game.batch,
                                                                  group=groups.g[self.layer + 1])
        if update_cost:
            self.update_cost()

    def update_cost(self):
        self.cost = {"money": 0}
        for x in range(UNIT_FORMATION_COLUMNS):
            for y in range(UNIT_FORMATION_ROWS):
                if self.units[x][y] != -1:
                    for key, value in possible_units[self.units[x][y]].get_cost([]).items():
                        if key in self.cost:
                            self.cost[key] += value
                        else:
                            self.cost[key] = value
        self.cost_count.text = client_utility.dict_to_string(self.cost)

    def detect_obstruction(self, size, x, y):
        for x2 in range(UNIT_FORMATION_COLUMNS):
            for y2 in range(UNIT_FORMATION_ROWS):
                if self.units[x2][y2] != -1 and not (x2 == x and y2 == y):
                    if UNIT_SIZE * distance(x, y, x2, y2) < (
                            size + unit_stats[possible_units[self.units[x2][y2]].name]["size"]) / 2:
                        return x2, y2
        return False


class UI_categories(client_utility.toolbar):
    def __init__(self, game, bottombar):
        super().__init__(0, bottombar.height, SCREEN_WIDTH, SCREEN_HEIGHT * 0.05, game.batch, layer=9)
        i = 0
        for _ in selects_all:
            self.add(bottombar.load_page, SCREEN_WIDTH * (0.01 + 0.1 * i), bottombar.height + SCREEN_HEIGHT * 0.005,
                     SCREEN_WIDTH * 0.09, SCREEN_HEIGHT * 0.04, args=(i,))
            i += 1


class UI_top_bar(client_utility.toolbar):
    def __init__(self, game: Game):
        self.height = SCREEN_HEIGHT * .05
        self.game = game
        super().__init__(0, SCREEN_HEIGHT - self.height, SCREEN_WIDTH, self.height, game.batch, layer=9)
        self.add(game.send_wave, self.height * 4, self.y, self.height * 3, self.height, text="send")
        self.add(game.centre_cam, self.height * 7, self.y, self.height, self.height, image=images.TargetButton)
        self.money = pyglet.text.Label(x=SCREEN_WIDTH * 0.995, y=SCREEN_HEIGHT * 0.995, text="Gold:0",
                                       color=(255, 240, 0, 255),
                                       group=groups.g[self.layer + 1], batch=self.batch, anchor_y="top",
                                       anchor_x="right",
                                       font_size=0.01 * SCREEN_WIDTH)
        self.mana = pyglet.text.Label(x=SCREEN_WIDTH * 0.85, y=SCREEN_HEIGHT * 0.995, text="Mana:0",
                                      color=(0, 150, 255, 255),
                                      group=groups.g[self.layer + 1], batch=self.batch, anchor_y="top",
                                      anchor_x="right",
                                      font_size=0.01 * SCREEN_WIDTH)
        timer_x_centre = self.height * 2
        timer_x_range = self.height * 2
        timer_y_centre = self.y + self.height * .85
        timer_y_range = self.height * .07
        self.timer = game.batch.add(
            8, pyglet.gl.GL_QUADS, groups.g[self.layer + 1],
            ("v2f", (timer_x_centre - timer_x_range, timer_y_centre - timer_y_range,
                     timer_x_centre - timer_x_range, timer_y_centre + timer_y_range,
                     timer_x_centre + timer_x_range, timer_y_centre + timer_y_range,
                     timer_x_centre + timer_x_range, timer_y_centre - timer_y_range,
                     timer_x_centre + timer_x_range, timer_y_centre - timer_y_range,
                     timer_x_centre + timer_x_range, timer_y_centre + timer_y_range,
                     timer_x_centre + timer_x_range, timer_y_centre + timer_y_range,
                     timer_x_centre + timer_x_range, timer_y_centre - timer_y_range)),
            ("c3B", (255, 0, 0, 255, 0, 0, 255, 0, 0, 255, 0, 0, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50))
        )
        self.timer_width = timer_x_range * 2
        self.last_wave_tick = 0
        self.timer_text = pyglet.text.Label(x=self.height * 2, y=self.y + self.height * .1, text="next wave in: 10",
                                            color=(255, 100, 0, 255),
                                            group=groups.g[self.layer + 1], batch=self.batch, anchor_y="bottom",
                                            anchor_x="center",
                                            font_size=0.01 * SCREEN_WIDTH)
        self.add(self.game.open_upgrade_menu, self.height * 8, self.y, self.height, self.height,
                 image=images.UpgradeButton)

    def update(self):
        x = self.timer_width * (self.last_wave_tick + WAVE_INTERVAL - self.game.ticks) / WAVE_INTERVAL
        self.timer.vertices[4:11:2] = [x] * 4
        self.timer_text.text = "next wave in: " + str(
            int((self.last_wave_tick + WAVE_INTERVAL - self.game.ticks) * INV_FPS) + 1)
        self.timer_text.text = str(self.game.ticks)


class minimap(client_utility.toolbar):
    def __init__(self, game: Game):
        super().__init__(0, int(SCREEN_HEIGHT * .25), int(SCREEN_HEIGHT * .3), int(SCREEN_HEIGHT * .3), game.batch,
                         image=images.UpgradeScreen, layer=9)
        self.game = game
        self.batch = game.batch
        self.view_range = 10000
        self.scale = self.width / self.view_range
        self.dot_scale = self.scale
        self.game.UI_toolbars.append(self)
        self.game.drawables.append(self)
        self.max_entities = 2000
        self.current_entity = 0
        self.already_checked = []
        self.sprite2 = game.batch.add(
            self.max_entities * 4, pyglet.gl.GL_QUADS, groups.g[self.layer + 1],
            ("v2i", (0,) * self.max_entities * 8),
            ("c4B", (255, 255, 255, 0) * self.max_entities * 4)
        )
        self.last_mouse_pos = (0, 0)
        self.cam_move_speed = 30
        self.lastupdate = 0

    def graphics_update(self, dt):
        self.lastupdate += 1
        if self.lastupdate != 5:
            return
        self.lastupdate = 0
        self.sprite2.vertices = [-1, 0] * self.max_entities * 4
        self.current_entity = 0
        self.already_checked = []
        [self.mark(e, (0, 0, 0, 255)) for e in self.game.all_obstacles]
        [self.mark(e, (0, 255, 0, 255)) for e in self.game.players[self.game.side].units]
        [self.mark(e, (0, 255, 0, 255)) for e in self.game.players[self.game.side].all_buildings]
        [self.mark(e, (255, 0, 0, 255)) for e in self.game.players[1 - self.game.side].units]
        [self.mark(e, (255, 0, 0, 255)) for e in self.game.players[1 - self.game.side].all_buildings]

    def mark(self, e, color):
        if self.current_entity >= self.max_entities:
            return
        location = (int((e.x - (
                self.game.camx + SCREEN_WIDTH / 2) / SPRITE_SIZE_MULT + self.view_range / 2) * self.scale),
                    int((e.y - (
                            self.game.camy + SCREEN_HEIGHT / 2) / SPRITE_SIZE_MULT + self.view_range / 2) * self.scale))
        dsize = max(int(e.size / 2 * self.dot_scale), 1)
        if -dsize < location[0] < self.width + dsize and -dsize < location[1] < self.width + dsize and \
                e not in self.already_checked:
            self.sprite2.colors[self.current_entity * 16: self.current_entity * 16 + 16] = color * 4
            self.sprite2.vertices[self.current_entity * 8:self.current_entity * 8 + 8] = (
                self.x + max(0, location[0] - dsize), self.y + max(0, location[1] - dsize),
                self.x + min(self.width, location[0] + dsize), self.y + max(0, location[1] - dsize),
                self.x + min(self.width, location[0] + dsize), self.y + min(self.width, location[1] + dsize),
                self.x + max(0, location[0] - dsize), self.y + min(self.width, location[1] + dsize))
            self.already_checked.append(e)
            self.current_entity += 1

    def mouse_click(self, x, y, button=0, modifiers=0):
        if super().mouse_click(x, y, button, modifiers):
            self.game.camx += (x - self.x - self.width / 2) / self.scale
            self.game.camy += (y - self.y - self.width / 2) / self.scale
            self.last_mouse_pos = (x, y)
            return True
        return False

    def mouse_drag(self, x, y, button=0, modifiers=0):
        if super().mouse_drag(x, y, button, modifiers):
            dx = x - self.last_mouse_pos[0]
            dy = y - self.last_mouse_pos[1]
            self.last_mouse_pos = (x, y)
            self.game.camx += dx * self.cam_move_speed
            self.game.camy += dy * self.cam_move_speed


class selection:
    unit_num = -1

    def __init__(self, game):
        self.cancelbutton = client_utility.button(self.end, SCREEN_WIDTH * 0.01, SCREEN_HEIGHT * 0.85,
                                                  SCREEN_WIDTH * 0.1, SCREEN_HEIGHT * 0.09, game.batch,
                                                  image=images.Cancelbutton)
        self.game = game

    def mouse_move(self, x, y):
        pass

    def key_press(self, button, modifiers):
        pass

    def mouse_click(self, x, y):
        pass

    def mouse_release(self, x, y):
        pass

    def end(self):
        self.game.selected = selection_none(self.game)
        self.cancelbutton.delete()

    def update_cam(self, x, y):
        pass

    def tick(self):
        pass

    def clicked_unit_slot(self, x, y):
        self.game.unit_formation.set_unit(x, y, self.unit_num)


class selection_none(selection):
    def __init__(self, game):
        self.game = game

    def end(self):
        pass

    @classmethod
    def is_unlocked(cls):
        print("how did we get here? 568")
        return True


class selection_building(selection):
    img = images.Towerbutton
    num = 0
    unit_num = -1

    def __init__(self, game):
        super().__init__(game)
        self.camx, self.camy = 0, 0
        self.entity_type = possible_buildings[self.num]
        self.size = unit_stats[self.entity_type.name]["size"]
        self.proximity = unit_stats[self.entity_type.name]["proximity"]
        self.sprite = pyglet.sprite.Sprite(self.entity_type.image, x=self.game.mousex,
                                           y=self.game.mousey, batch=game.batch,
                                           group=groups.g[2])
        self.sprite.scale = self.size / self.sprite.width * SPRITE_SIZE_MULT
        self.sprite.opacity = 100
        self.update_cam(self.game.camx, self.game.camy)

    def mouse_move(self, x, y):
        self.sprite.update(x=x, y=y)
        self.cancelbutton.mouse_move(x, y)

    def mouse_click(self, x, y):
        if not self.cancelbutton.mouse_click(x, y):
            for e in self.game.players[1].all_buildings:
                if e.prevents_placement and e.distance_to_point((x + self.camx) / SPRITE_SIZE_MULT,
                                                                (y + self.camy) / SPRITE_SIZE_MULT) < self.size / 2:
                    return
            for e in self.game.players[0].all_buildings:
                if e.prevents_placement and e.distance_to_point((x + self.camx) / SPRITE_SIZE_MULT,
                                                                (y + self.camy) / SPRITE_SIZE_MULT) < self.size / 2:
                    return
            close_to_friendly = False
            for e in self.game.players[self.game.side].all_buildings:
                if e.distance_to_point((x + self.camx) / SPRITE_SIZE_MULT,
                                       (y + self.camy) / SPRITE_SIZE_MULT) < self.proximity:
                    close_to_friendly = True
            if not close_to_friendly:
                return
            self.game.connection.Send({"action": "place_building", "xy": [(x + self.camx) / SPRITE_SIZE_MULT,
                                                                          (y + self.camy) / SPRITE_SIZE_MULT],
                                       "entity_type": self.num})
            self.end()

    def mouse_release(self, x, y):
        self.cancelbutton.mouse_release(x, y)

    def end(self):
        self.sprite.delete()
        super().end()

    def update_cam(self, x, y):
        self.camx, self.camy = x, y

    @classmethod
    def is_unlocked(cls, game):
        return game.players[game.side].has_unit(possible_buildings[cls.num])


class selection_tower(selection_building):
    img = images.Towerbutton
    num = 0


class selection_farm(selection_building):
    img = images.Farm
    num = 1


class selection_wall(selection):
    img = images.Towerbutton

    def __init__(self, game):
        super().__init__(game)
        self.selected1, self.selected2 = None, None
        self.buttons = []
        self.camx, self.camy = game.camx, game.camy
        for e in game.players[game.side].all_buildings:
            if e.entity_type == "tower":
                self.buttons.append(
                    client_utility.button(self.select, (e.x - 20) * SPRITE_SIZE_MULT, (e.y - 20) * SPRITE_SIZE_MULT,
                                          40 * SPRITE_SIZE_MULT, 40 * SPRITE_SIZE_MULT,
                                          self.game.batch, args=(e.ID,)))
        self.sprite = None
        self.update_cam(self.game.camx, self.game.camy)

    def select(self, ID):
        if self.selected1 is None or self.selected1 == ID:
            self.selected1 = ID
            return
        self.selected2 = ID
        self.game.connection.Send({"action": "place_wall", "ID1": self.selected1,
                                   "ID2": self.selected2})
        self.end()

    def mouse_move(self, x, y):
        pass

    def mouse_click(self, x, y):
        if not self.cancelbutton.mouse_click(x, y):
            [e.mouse_click(x, y) for e in self.buttons]

    def mouse_release(self, x, y):
        self.cancelbutton.mouse_release(x, y)
        i = 0
        while len(self.buttons) > i:
            self.buttons[i].mouse_release(x, y)
            i += 1

    def end(self):
        super().end()
        [e.delete() for e in self.buttons]
        self.buttons = []

    def update_cam(self, x, y):
        [e.update(e.ogx - x, e.ogy - y) for e in self.buttons]
        self.camx, self.camy = x, y

    @classmethod
    def is_unlocked(cls, game):
        return game.players[game.side].has_unit(Wall)


class selection_unit_formation(selection):
    img = images.Farm

    def __init__(self, game):
        super().__init__(game)
        self.troops = self.game.unit_formation.units
        self.sprites = []
        self.camx, self.camy = game.camx, game.camy
        for x in range(self.game.unit_formation_columns):
            for y in range(self.game.unit_formation_rows):
                if self.troops[x][y] != -1:
                    x_location = ((x - self.game.unit_formation_columns * .5) * UNIT_SIZE +
                                  self.game.players[self.game.side].TownHall.x) * SPRITE_SIZE_MULT - self.camx
                    y_location = ((y - self.game.unit_formation_rows * .5) * UNIT_SIZE +
                                  self.game.players[self.game.side].TownHall.y) * SPRITE_SIZE_MULT - self.camy
                    self.sprites.append(client_utility.sprite_with_scale(*possible_units[self.troops[x][y]].get_image(),
                                                                         x=x_location,
                                                                         y=y_location,
                                                                         group=groups.g[5],
                                                                         batch=self.game.batch))
        self.current_pos = [self.game.players[self.game.side].TownHall.x * SPRITE_SIZE_MULT,
                            self.game.players[self.game.side].TownHall.y * SPRITE_SIZE_MULT]
        self.instructions = []
        self.mouse_pos = [self.game.players[self.game.side].TownHall.x, self.game.players[self.game.side].TownHall.y]
        self.image = images.blue_arrow
        self.actual_indicator_points = [0 for thisIsaLongWordThatiJustMadeJustBecauseiCanLmaoGetRekt in range(8)]
        moving_indicator_texgroup = client_utility.TextureBindGroup(self.image, layer=3)
        self.MI_width = SCREEN_HEIGHT / 20
        self.repeated_img_height = self.image.height * 2 * self.MI_width / self.image.width
        self.moving_indicator = game.batch.add(4, pyglet.gl.GL_QUADS, moving_indicator_texgroup,
                                               "v2f",
                                               "t2f",
                                               )
        self.indicator_cycling = 0
        self.moving_indicator_points = 1
        self.update_moving_indicator_pos(500, 500)

    def mouse_move(self, x, y):
        self.update_moving_indicator_pos(x + self.camx, y + self.camy)
        self.mouse_pos = [x, y]

    def update_moving_indicator_pos(self, x, y):
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        dx = self.current_pos[0] - x
        dy = self.current_pos[1] - y
        if 0 == dx == dy:
            return
        length = (dx ** 2 + dy ** 2) ** 0.5
        scale = self.MI_width / length
        dx *= scale
        dy *= scale
        self.moving_indicator.vertices[-8::] = [x - dy - self.camx,
                                                y + dx - self.camy,
                                                x + dy - self.camx,
                                                y - dx - self.camy,
                                                self.current_pos[0] + dy - self.camx,
                                                self.current_pos[1] - dx - self.camy,
                                                self.current_pos[0] - dy - self.camx,
                                                self.current_pos[1] + dx - self.camy
                                                ]
        self.actual_indicator_points[-8::] = [x - dy,
                                              y + dx,
                                              x + dy,
                                              y - dx,
                                              self.current_pos[0] + dy,
                                              self.current_pos[1] - dx,
                                              self.current_pos[0] - dy,
                                              self.current_pos[1] + dx
                                              ]
        self.moving_indicator.tex_coords[-8::] = [0, self.indicator_cycling,
                                                  1, self.indicator_cycling,
                                                  1, length / self.repeated_img_height + self.indicator_cycling,
                                                  0, length / self.repeated_img_height + self.indicator_cycling
                                                  ]

    def add_indicator_point(self, x, y):
        self.moving_indicator_points += 1
        self.moving_indicator.resize(self.moving_indicator_points * 4)
        self.update_moving_indicator_pos(x, y)

    def mouse_click(self, x, y):
        for e in self.game.players[1 - self.game.side].all_buildings:
            if e.distance_to_point((x + self.camx) / SPRITE_SIZE_MULT, (y + self.camy) / SPRITE_SIZE_MULT) <= 0:
                self.instructions.append(["attack", e.ID])
                visx, visy = e.x * SPRITE_SIZE_MULT, e.y * SPRITE_SIZE_MULT
                self.update_moving_indicator_pos(visx, visy)
                self.actual_indicator_points += [0 for _ in range(8)]
                self.current_pos = [visx, visy]
                self.add_indicator_point(visx, visy)
                return
        for e in self.game.players[1 - self.game.side].walls:
            if e.distance_to_point((x + self.camx) / SPRITE_SIZE_MULT, (y + self.camy) / SPRITE_SIZE_MULT) <= 0:
                self.instructions.append(["attack", e.ID])
                visx, visy = e.x * SPRITE_SIZE_MULT, e.y * SPRITE_SIZE_MULT
                self.update_moving_indicator_pos(visx, visy)
                self.actual_indicator_points += [0 for _ in range(8)]
                self.current_pos = [visx, visy]
                self.add_indicator_point(visx, visy)
                return
        for e in self.game.players[1 - self.game.side].units:
            if e.distance_to_point((x + self.camx) / SPRITE_SIZE_MULT, (y + self.camy) / SPRITE_SIZE_MULT) <= \
                    100 * SPRITE_SIZE_MULT:
                self.instructions.append(["attack", e.formation.ID])
                visx, visy = e.x * SPRITE_SIZE_MULT, e.y * SPRITE_SIZE_MULT
                self.update_moving_indicator_pos(visx, visy)
                self.actual_indicator_points += [0 for _ in range(8)]
                self.current_pos = [visx, visy]
                self.add_indicator_point(visx, visy)
                return
        if not self.cancelbutton.mouse_click(x, y) and [x + self.camx, y + self.camy] != self.current_pos:
            self.instructions.append(["walk", (x + self.camx) / SPRITE_SIZE_MULT,
                                      (y + self.camy) / SPRITE_SIZE_MULT])
            self.actual_indicator_points += [0 for _ in range(8)]
            self.add_indicator_point(x + self.camx, y + self.camy)
            self.current_pos = [x + self.camx, y + self.camy]

    def mouse_release(self, x, y):
        self.cancelbutton.mouse_release(x, y)

    def end(self):
        [e.delete() for e in self.sprites]
        self.moving_indicator.delete()
        super().end()

    def tick(self):
        self.indicator_cycling += 0.016
        reduce = 0
        if self.indicator_cycling >= 1:
            self.indicator_cycling -= 1
            reduce = 1
        mi = self.moving_indicator.tex_coords
        for i in range(1, len(mi), 2):
            mi[i] += 0.016 - reduce

    def update_cam(self, x, y):
        dx, dy = x - self.camx, y - self.camy
        self.camx, self.camy = x, y
        for i in range(0, self.moving_indicator_points * 8, 2):
            self.moving_indicator.vertices[i] = self.actual_indicator_points[i] - x
        for i in range(1, self.moving_indicator_points * 8, 2):
            self.moving_indicator.vertices[i] = self.actual_indicator_points[i] - y
        self.update_moving_indicator_pos(self.mouse_pos[0] + x, self.mouse_pos[1] + y)
        for e in self.sprites:
            e.update(x=e.x - dx, y=e.y - dy)

    def key_press(self, button, modifiers):
        if button == key.ENTER:
            self.game.connection.Send(
                {"action": "summon_formation", "instructions": self.instructions, "troops": self.troops})
            self.end()

    @classmethod
    def is_unlocked(cls):
        print("how did we get here? 811")
        return True


class selection_unit(selection):
    img = images.Farm
    unit_num = 0

    def mouse_click(self, x, y):
        if not self.cancelbutton.mouse_click(x, y):
            pass

    def mouse_release(self, x, y):
        self.cancelbutton.mouse_release(x, y)

    @classmethod
    def is_unlocked(cls, game):
        return game.players[game.side].has_unit(possible_units[cls.unit_num])


class selection_spell(selection):
    index = 0
    spell_name = "Fireball"

    def __init__(self, game: Game):
        super().__init__(game)
        self.sprite = pyglet.sprite.Sprite(images.Shockwave, batch=game.batch, group=groups.g[4])
        self.sprite.scale = unit_stats[possible_spells[self.index].name]["radius"] * 2 / \
                            images.Shockwave.width * SPRITE_SIZE_MULT
        self.label = pyglet.text.Label(client_utility.dict_to_string(possible_spells[self.index].get_cost()),
                                       font_size=int(20 * SPRITE_SIZE_MULT), color=(50, 200, 255, 255),
                                       batch=game.batch, group=groups.g[5], anchor_x="center", anchor_y="bottom")

    def mouse_move(self, x, y):
        self.sprite.update(x=x, y=y)
        self.label.x = x
        self.label.y = y

    def mouse_click(self, x, y):
        if not self.cancelbutton.mouse_click(x, y):
            self.game.connection.Send(
                {"action": "spell", "num": self.index, "x": (x + self.game.camx) / SPRITE_SIZE_MULT,
                 "y": (y + self.game.camy) / SPRITE_SIZE_MULT})
            self.end()

    def end(self):
        self.sprite.delete()
        self.label.delete()
        super().end()

    @classmethod
    def is_unlocked(cls, game):
        return game.players[game.side].has_unit(possible_spells[cls.index])


class selection_fireball(selection_spell):
    index = 0
    img = images.Meteor


class selection_freeze(selection_spell):
    index = 1
    img = images.Freeze


class selection_rage(selection_spell):
    index = 2
    img = images.RageIcon


class selection_tree(selection_spell):
    index = 3
    img = images.MagicTree


class building_upgrade_menu(client_utility.toolbar):
    def __init__(self, building_ID, game: Game):
        self.target = game.find_building(building_ID, game.side)
        if not self.target.upgrades_into:
            return
        buttonsize = SCREEN_WIDTH * .1
        amount = 0
        for e in self.target.upgrades_into:
            if game.players[game.side].has_unit(e):
                amount += 1
        if amount == 0:
            return
        self.width = buttonsize * amount
        self.height = buttonsize
        super().__init__(self.target.x * SPRITE_SIZE_MULT - game.camx - self.width / 2,
                         self.target.y * SPRITE_SIZE_MULT - game.camy - self.height / 2, self.width, self.height,
                         game.batch, layer=9)
        self.game = game
        game.mouse_click_detectors.append(self)
        i = 0
        j = 0
        self.texts = []
        for e in self.target.upgrades_into:
            if game.players[game.side].has_unit(e):
                self.texts.append(pyglet.text.Label(
                    x=self.target.x * SPRITE_SIZE_MULT - game.camx - self.width / 2 + buttonsize * (i + .5),
                    y=self.target.y * SPRITE_SIZE_MULT - game.camy - self.height / 2,
                    text=client_utility.dict_to_string(e.get_cost([])),
                    color=(255, 240, 0, 255),
                    group=groups.g[self.layer + 2], batch=game.batch, anchor_y="bottom", anchor_x="center",
                    multiline=True,
                    width=buttonsize,
                    font_size=0.00625 * SCREEN_WIDTH))
                self.add(self.clicked_button,
                         self.target.x * SPRITE_SIZE_MULT - game.camx - self.width / 2 + buttonsize * i,
                         self.target.y * SPRITE_SIZE_MULT - game.camy - self.height / 2, buttonsize,
                         buttonsize, e.image, args=(j,))
                i += 1
            j += 1

    def clicked_button(self, i):
        if not self.target.exists:
            self.close()
            return
        self.game.connection.Send({"action": "buy upgrade", "building ID": self.target.ID, "upgrade num": i})
        self.close()

    def mouse_click(self, x, y, button=0, modifiers=0):
        if self.x + self.width >= x >= self.x and self.y + self.height >= y >= self.y:
            [e.mouse_click(x, y) for e in self.buttons]
            return True
        self.close()
        return False

    def close(self):
        [e.delete() for e in self.texts]
        self.game.mouse_click_detectors.remove(self)
        self.delete()


class obstacle_vertexlist:
    def __init__(self, game):
        self.size = MOUNTAINS * MOUNTAINRANGES
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        self.sprite = game.batch.add(
            self.size * 4, pyglet.gl.GL_QUADS, client_utility.TextureBindGroup(images.Mountain, layer=1),
            ("v2f", (0, 0) * self.size * 4),
            ("t2f/static", (0, 0, 1, 0, 1, 1, 0, 1) * self.size),
            ("c4B/static", (255, 255, 255, 255) * self.size * 4)
        )
        self.current_index = 0
        self.camx, self.camy = game.camx, game.camy
        self.actual_vertices = []

    def add(self, x, y, size):
        size /= 2
        x *= SPRITE_SIZE_MULT
        x -= self.camx
        y *= SPRITE_SIZE_MULT
        y -= self.camy
        size *= SPRITE_SIZE_MULT
        self.sprite.vertices[self.current_index:self.current_index + 8] = (x - size, y - size,
                                                                           x + size, y - size,
                                                                           x + size, y + size,
                                                                           x - size, y + size)
        self.current_index += 8
        self.actual_vertices += (x - size, y - size, x + size, y - size, x + size, y + size, x - size, y + size)

    def update_cam(self, x, y):
        dx, dy = x - self.camx, y - self.camy
        self.camx, self.camy = x, y
        self.sprite.vertices -= np.array([dx, dy] * self.size * 4)


class Obstacle:
    prevents_placement = False
    img = images.Boulder
    pathing_cost = 5

    def __init__(self, x, y, size, game: Game):
        self.x, self.y, self.size, self.game = x, y, size, game
        chunks = get_chunks(x, y, size)
        for e in chunks:
            game.add_obstacle_to_chunk(self, e)

        game.obstacles_vlist.add(x, y, size)
        game.all_obstacles.append(self)

    def collide(self, e):
        if not e.exists or (self.x - e.x) ** 2 + (self.y - e.y) ** 2 > (e.size + self.size) ** 2 / 4:
            return
        effect_combined((effect_stat_mult, effect_stat_mult),
                        (("speed", constants.MOUNTAIN_SLOWDOWN), ("mass", 1 / constants.MOUNTAIN_SLOWDOWN)),
                        2, "mountain").apply(e)


class Building:
    name = "TownHall"
    entity_type = "townhall"
    image = images.Tower
    prevents_placement = True

    def __init__(self, x, y, tick, side, game, instant=False, size_override=None, group_override=2):
        x, y = int(x), int(y)
        self.spawning = game.ticks - tick
        self.sounds = noise.sounds[self.name]
        self.ID = (x, y, self.name, tick)
        self.shown = True
        self.x, self.y = x, y
        self.side = side
        self.size = unit_stats[self.name]["size"] if size_override is None else size_override
        self.health = unit_stats[self.name]["health"]
        self.sprite = pyglet.sprite.Sprite(self.image, x=x * SPRITE_SIZE_MULT - game.camx,
                                           y=y * SPRITE_SIZE_MULT - game.camy, batch=game.batch,
                                           group=groups.g[group_override])
        self.sprite.scale = self.size * SPRITE_SIZE_MULT / self.sprite.width
        self.game = game
        self.chunks = get_chunks_force_circle(x, y, self.size)
        self.exists = instant
        self.game.players[side].all_buildings.append(self)
        for e in self.chunks:
            game.add_building_to_chunk(self, e)
        self.collision_chunks = []
        for c in self.chunks:
            self.collision_chunks.append(self.game.chunks[c])
        hpbar_y_centre = self.sprite.y
        hpbar_y_range = 2 * SPRITE_SIZE_MULT
        hpbar_x_centre = self.sprite.x
        hpbar_x_range = self.size * SPRITE_SIZE_MULT / 2
        self.hpbar = game.batch.add(
            8, pyglet.gl.GL_QUADS, groups.g[7],
            ("v2f", (hpbar_x_centre - hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre - hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range)),
            ("c3B/static", (0, 255, 0, 0, 255, 0, 0, 255, 0, 0, 255, 0, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50)
            if self.game.side == self.side else (
                163, 73, 163, 163, 73, 163, 163, 73, 163, 163, 73, 163, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50))
        )
        self.sprite.opacity = 255 if instant else 70
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

    def show(self):
        self.sprite.batch = self.game.batch
        self.shown = True
        [e.graphics_show() for e in self.effects]

    def hide(self):
        self.sprite.batch = None
        self.shown = False
        [e.graphics_hide() for e in self.effects]

    def update_stats(self, stats=None):
        if not self.exists:
            return
        health_part = self.health / self.stats["health"]
        if stats is None:
            stats = self.stats.keys()
        for e in stats:
            self.stats[e] = (self.base_stats[e] + sum(self.mods_add[e])) * product(*self.mods_multiply[e])
        self.health = self.stats["health"] * health_part
        self.sprite.scale *= self.stats["size"] / self.size
        self.size = self.stats["size"]

    def towards(self, x, y):
        dx, dy = self.x - x, self.y - y
        invh = inv_h(dx, dy)
        return dx * invh, dy * invh

    def update_hpbar(self):
        if self.hpbar is None:
            return
        hpbar_y_centre = self.sprite.y
        hpbar_y_range = 2 * SPRITE_SIZE_MULT
        hpbar_x_centre = self.sprite.x
        hpbar_x_range = self.size * SPRITE_SIZE_MULT / 2
        health_size = hpbar_x_range * (2 * self.health / self.stats["health"] - 1)
        self.hpbar.vertices = (hpbar_x_centre - hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                               hpbar_x_centre - hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre - hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre - hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range)

    def take_damage(self, amount, source, type=None):
        if self.exists:
            if type is not None:
                if type + "_resistance" in self.stats.keys():
                    amount *= self.stats[type + "_resistance"]
            self.health -= amount * self.stats["resistance"]
            if self.health <= 0:
                self.die()

    def on_delete(self):
        pass

    def on_die(self):
        pass

    def die(self):
        if not self.exists:
            return
        self.delete()
        self.on_die()
        noise.play(self.name, "die")

    def delete(self):
        if not self.exists:
            return
        self.game.players[self.side].all_buildings.remove(self)
        self.sprite.delete()
        for e in self.chunks:
            self.game.remove_building_from_chunk(self, e)
        self.hpbar.delete()
        self.exists = False
        while self.effects:
            self.effects[0].on_death()
            self.effects[0].remove()
        self.on_delete()

    def distance_to_point(self, x, y):
        return distance(self.x, self.y, x, y) - self.size / 2

    def fast_point_dist(self, x, y):
        return abs(self.x - x) + abs(self.y - y) - self.size / 2

    def update_cam(self, x, y):
        x, y = self.x * SPRITE_SIZE_MULT - x, self.y * SPRITE_SIZE_MULT - y
        if self.shown:
            self.sprite.update(x=x, y=y)
            if x + self.size < 0 or x - self.size > SCREEN_WIDTH or y + self.size < 0 or y - self.size > SCREEN_HEIGHT:
                self.hide()
                self.update_hpbar()
                return
        elif x + self.size > 0 and x - self.size < SCREEN_WIDTH and y + self.size > 0 and y - self.size < SCREEN_HEIGHT:
            self.show()

    def tick(self):
        if self.spawning < FPS * ACTION_DELAY:
            self.spawning += 1
        if self.spawning >= FPS * ACTION_DELAY:
            self.exists = True
            self.sprite.opacity = 255
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

    def graphics_update(self, dt):
        if self.shown:
            self.update_hpbar()
            [e.graphics_update(dt) for e in self.effects]


class RangedBuilding(Building):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_cooldown = 0
        self.target = None
        self.shooting_in_chunks = get_chunks_force_circle(self.x, self.y, 2 * self.stats["reach"])
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
                    noise.play(self.name, "attack")
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


class TownHall(Building):
    name = "TownHall"
    entity_type = "townhall"
    image = images.Townhall
    upgrades = []

    def __init__(self, x, y, side, game):
        super().__init__(x, y, 0, side, game)
        self.exists = True
        self.sprite.opacity = 255
        self.tick = self.tick2
        self.upgrades_into = [TownHall1]

    def on_die(self):
        animation_explosion(self.x, self.y, 1000, 30, self.game)
        for i in range(10):
            animation_explosion(self.x + random.randint(-150, 150), self.y + random.randint(-150, 150),
                                random.randint(100, 500), random.randint(10, 30), self.game)
        print("game over", self.game.ticks, self.game.players[self.side].resources)
        noise.TH_death.play()

    def tick(self):
        if self.spawning < FPS * ACTION_DELAY:
            self.spawning += 1
        if self.spawning >= FPS * ACTION_DELAY:
            self.exists = True
            self.sprite.opacity = 255
            self.tick = self.tick2
            self.update_stats()
            if self.comes_from is not None:
                self.comes_from.delete()


class TownHall_upgrade(Building):
    upgrades = []
    name = "TownHall"
    entity_type = "townhall"

    def __init__(self, target=None, tick=None, x=None, y=None, side=None, game=None, ID=None):
        if target is not None:
            super().__init__(target.x, target.y, tick, target.side, target.game)
            self.comes_from = target
            target.game.players[target.side].force_purchase(self.get_cost([]))
        else:
            super().__init__(x, y, tick, side, game)
            self.comes_from = None
            game.players[side].force_purchase(self.get_cost([]))
        self.game.players[self.side].TownHall = self
        self.upgrades_into = [e for e in self.upgrades]

    def on_die(self):
        animation_explosion(self.x, self.y, 1000, 30, self.game)
        for i in range(10):
            animation_explosion(self.x + random.randint(-150, 150), self.y + random.randint(-150, 150),
                                random.randint(100, 500), random.randint(10, 30), self.game)
        print("game over", self.game.ticks)
        noise.TH_death.play()

    @classmethod
    def get_cost(cls, params=()):
        resources = {"money": unit_stats[cls.name]["cost"]}
        for e in unit_stats[cls.name].keys():
            if e.startswith("cost_"):
                resources[e[5::]] = unit_stats[cls.name][e]
        return resources


class TownHall1(TownHall_upgrade, RangedBuilding):
    upgrades = []
    name = "TownHall1"
    image = images.Townhall

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_cooldown = 0
        self.target = None
        self.shooting_in_chunks = get_chunks_force_circle(self.x, self.y, 2 * self.stats["reach"])
        self.turns_without_target = 0

    def attack(self, target):
        direction = target.towards(self.x, self.y)
        Arrow(self.x, self.y, *direction, self.game, self.side, self.stats["dmg"], self, self.stats["bulletspeed"],
              self.stats["reach"] * 1.5, scale=self.stats["bullet_scale"], pierce=self.stats["pierce"],
              cluster=self.stats["cluster"], recursion=self.stats["recursion"])


class TownHall11(TownHall_upgrade):
    upgrades = []
    name = "TownHall11"
    image = images.Meteor

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
        a = animation_frost(self.x, self.y, self.stats["radius"], None, self.game)
        if hasattr(a, "sprite"):
            self.additionals.append(a)

    def on_delete(self):
        [e.delete() for e in self.additionals]


class TownHall12(TownHall_upgrade, RangedBuilding):
    upgrades = []
    name = "TownHall12"
    image = images.Townhall

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_cooldown = 0
        self.target = None
        self.shooting_in_chunks = get_chunks_force_circle(self.x, self.y, 2 * self.stats["reach"])
        self.turns_without_target = 0

    def attack(self, target):
        direction = target.towards(self.x, self.y)
        flame_wave(self.x, self.y, *direction, self.game, self.side, self.stats["dmg"], self, self.stats["bulletspeed"],
                   self.stats["reach"] * 1.5, self.stats["bullet_size"], scale=self.stats["bullet_size"],
                   pierce=self.stats["pierce"],
                   cluster=self.stats["cluster"], recursion=self.stats["recursion"])


class TownHall13(TownHall_upgrade):
    upgrades = []
    name = "TownHall13"
    image = images.blue_arrow

    def on_summon(self):
        for i in range(int(self.stats["trees"])):
            size = self.stats["tree_size"] * (math.sin(self.game.ticks ** i) + 1)
            dist = self.stats["spread"] * abs(math.sin(self.game.ticks * 2 ** i))
            Tree(self.x + math.cos(self.game.ticks * 3 ** i) * dist, self.y + math.sin(self.game.ticks * 3 ** i) * dist,
                 self.side, self.game, size)


class TownHall14(TownHall_upgrade):
    upgrades = []
    name = "TownHall14"
    image = images.Fire


class Tree(Building):
    name = "Tree"
    entity_type = "tree"
    image = images.Tree
    upgrades = []
    prevents_placement = False

    def __init__(self, x, y, side, game, size, health=None):
        size = max(.1, size)
        super().__init__(x, y, game.ticks, side, game, size_override=size * unit_stats[self.name]["size"],
                         group_override=6)
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
        a = animation_frost(self.x, self.y, self.bigness * self.stats["diameter"], None, self.game, opacity=50,
                            image=images.Nature)
        if hasattr(a, "sprite"):
            self.additionals.append(a)

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


class Tower(RangedBuilding):
    name = "Tower"
    entity_type = "tower"
    image = images.Tower
    upgrades = []

    def __init__(self, x, y, tick, side, game):
        game.players[side].force_purchase(self.get_cost([]))
        super().__init__(x, y, tick, side, game)
        self.sprite2 = pyglet.sprite.Sprite(images.TowerCrack, x=x * SPRITE_SIZE_MULT,
                                            y=y * SPRITE_SIZE_MULT, batch=game.batch,
                                            group=groups.g[4])
        self.sprite2.opacity = 0
        self.sprite2.scale = self.size * SPRITE_SIZE_MULT / self.sprite2.width
        self.upgrades_into = [e for e in self.upgrades]

    @classmethod
    def get_cost(cls, params=()):
        resources = {"money": unit_stats[cls.name]["cost"]}
        for e in unit_stats[cls.name].keys():
            if e.startswith("cost_"):
                resources[e[5::]] = unit_stats[cls.name][e]
        return resources

    def on_delete(self):
        self.sprite2.delete()

    def attack(self, target):
        direction = target.towards(self.x, self.y)
        self.sprite.rotation = 90 - get_rotation_norm(*direction) * 180 / math.pi
        Arrow(self.x, self.y, *direction, self.game, self.side, self.stats["dmg"], self, self.stats["bulletspeed"],
              self.stats["reach"] * 1.5, scale=self.stats["bullet_scale"], pierce=self.stats["pierce"],
              cluster=self.stats["cluster"], recursion=self.stats["recursion"])

    def update_hpbar(self):
        super().update_hpbar()
        if self.shown:
            self.sprite2.opacity = 255 * max(0, (self.stats["health"] - self.health)) / self.stats["health"]

    def update_cam(self, x, y):
        super().update_cam(x, y)
        if self.shown:
            self.sprite2.update(x=self.x * SPRITE_SIZE_MULT - x, y=self.y * SPRITE_SIZE_MULT - y)

    def show(self):
        self.sprite.batch = self.game.batch
        self.sprite2.batch = self.game.batch
        self.shown = True

    def hide(self):
        self.sprite.batch = None
        self.sprite2.batch = None
        self.shown = False


class tower_upgrade(Tower):
    upgrades = []
    name = "Tower"

    def __init__(self, target=None, tick=None, x=None, y=None, side=None, game=None, ID=None):
        if target is not None:
            super().__init__(target.x, target.y, tick, target.side, target.game)
            self.comes_from = target
            self.ID = target.ID
        else:
            super().__init__(x, y, tick, side, game)
            self.ID = ID
            self.comes_from = None
        self.upgrades_into = [e for e in self.upgrades]

    @classmethod
    def get_cost(cls, params=()):
        resources = {"money": unit_stats[cls.name]["cost"]}
        for e in unit_stats[cls.name].keys():
            if e.startswith("cost_"):
                resources[e[5::]] = unit_stats[cls.name][e]
        return resources


class Tower1(tower_upgrade, Tower):
    name = "Tower1"
    image = images.Tower1
    upgrades = []


class Tower2(tower_upgrade, Tower):
    name = "Tower2"
    image = images.Tower2
    upgrades = []

    def attack(self, target):
        direction = target.towards(self.x, self.y)
        self.sprite.rotation = 90 - get_rotation_norm(*direction) * 180 / math.pi
        Boulder(self.x, self.y, *direction, self.game, self.side, self.stats["dmg"], self, self.stats["bulletspeed"],
                target.distance_to_point(self.x, self.y), self.stats["explosion_radius"],
                scale=self.stats["bullet_scale"], pierce=self.stats["pierce"], cluster=self.stats["cluster"],
                recursion=self.stats["recursion"])


class Tower4(tower_upgrade, Tower):
    name = "Tower4"
    image = images.Tower4
    upgrades = []


class Tower41(tower_upgrade, Tower):
    name = "Tower41"
    image = images.Tower41
    upgrades = []


class Tower23(tower_upgrade, Tower):
    name = "Tower23"
    image = images.Tower23
    upgrades = []

    def attack(self, target):
        AOE_damage(self.x, self.y, self.stats["reach"], self.stats["dmg"], self, self.game)
        animation_ring_of_fire(self.x, self.y, self.stats["reach"] * 3, self.game)


class Tower231(tower_upgrade, Tower):
    name = "Tower231"
    image = images.Tower23
    upgrades = []

    def attack(self, target):
        AOE_damage(self.x, self.y, self.stats["flame_radius"], self.stats["dmg2"], self, self.game)
        animation_ring_of_fire(self.x, self.y, self.stats["flame_radius"] * 3, self.game)
        direction = target.towards(self.x, self.y)
        self.sprite.rotation = 90 - get_rotation_norm(*direction) * 180 / math.pi
        flame_wave(self.x, self.y, *direction, self.game, self.side, self.stats["dmg"], self, self.stats["bulletspeed"],
                   self.stats["reach"] * 1.2, self.stats["bullet_size"], scale=self.stats["bullet_size"],
                   pierce=self.stats["pierce"], cluster=self.stats["cluster"], recursion=self.stats["recursion"])


class Tower22(tower_upgrade, Tower):
    name = "Tower22"
    image = images.Tower22
    upgrades = []

    def attack(self, target):
        if target is None:
            angle = self.game.ticks ** 2
            dist = self.stats["reach"] * abs(math.sin(self.game.ticks))
            dx = dist * math.cos(angle)
            dy = dist * math.sin(angle)
        else:
            dx, dy = target.x - self.x, target.y - self.y
        self.sprite.rotation = 90 - get_rotation(dx, dy) * 180 / math.pi
        Mine(self.x, self.y, dx, dy, self.game, self.side, self.stats["dmg"], self,
             self.stats["bulletspeed"],
             hypot(dx, dy), self.stats["explosion_radius"], self.stats["duration"],
             scale=self.stats["bullet_scale"], pierce=self.stats["pierce"], cluster=self.stats["cluster"],
             recursion=self.stats["recursion"])

    def tick2(self):
        super().tick2()
        if self.current_cooldown > 0:
            self.current_cooldown -= 1 * INV_FPS
        if self.current_cooldown <= 0:
            self.current_cooldown += self.stats["cd"]
            noise.play(self.name, "attack")
            if self.acquire_target():
                self.attack(self.target)
            else:
                self.turns_without_target += 1
                self.attack(None)


class Tower221(tower_upgrade, Tower):
    name = "Tower221"
    image = images.Tower221
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
            noise.play(self.name, "attack")
            self.attack(None)


class Turret(RangedBuilding):
    name = "Turret"
    entity_type = "tower"
    image = images.Turret
    upgrades = []
    prevents_placement = False

    def __init__(self, x, y, stats, lifetime, side, game, alt_attack=None):
        if "size" in stats:
            super().__init__(x, y, game.ticks, side, game, instant=True, size_override=stats["size"])
        else:
            super().__init__(x, y, game.ticks, side, game, instant=True)
        for s in stats:
            self.base_stats[s] = stats[s]
        self.lifetime = lifetime
        self.update_stats()
        self.shooting_in_chunks = get_chunks_force_circle(self.x, self.y, 2 * self.stats["reach"])
        if alt_attack is not None:
            self.attack = alt_attack

    def tick2(self):
        super().tick2()
        self.lifetime -= INV_FPS
        if self.lifetime <= 0:
            self.delete()

    def attack(self, target):
        direction = get_rotation_norm(*target.towards(self.x, self.y))
        self.sprite.rotation = 90 - direction / math.pi
        Bullet(self.x, self.y, direction, self.game, self.side, self.stats["dmg"], self, self.stats["bulletspeed"],
               self.stats["reach"] * 1.5, scale=self.stats["bullet_scale"], pierce=self.stats["pierce"],
               cluster=self.stats["cluster"], recursion=self.stats["recursion"])


class Tower21(tower_upgrade, Tower):
    name = "Tower21"
    image = images.Tower21
    upgrades = []

    def attack(self, target):
        direction = target.towards(self.x, self.y)
        self.sprite.rotation = 90 - get_rotation_norm(*direction) * 180 / math.pi
        Meteor(self.x, self.y, *direction, self.game, self.side, self.stats["dmg"], self, self.stats["bulletspeed"],
               target.distance_to_point(self.x, self.y), self.stats["explosion_radius"],
               scale=self.stats["bullet_scale"], pierce=self.stats["pierce"], cluster=self.stats["cluster"],
               recursion=self.stats["recursion"])


class Tower211(tower_upgrade, Tower):
    name = "Tower211"
    image = images.Tower21
    upgrades = []

    def attack(self, target):
        direction = target.towards(self.x, self.y)
        self.sprite.rotation = 90 - get_rotation_norm(*direction) * 180 / math.pi
        Egg(self.x, self.y, *direction, self.game, self.side, self.stats["dmg"], self, self.stats["bulletspeed"],
            target.distance_to_point(self.x, self.y), self.stats["explosion_radius"], scale=self.stats["bullet_scale"],
            pierce=self.stats["pierce"], cluster=self.stats["cluster"], recursion=self.stats["recursion"])


class Tower11(tower_upgrade, Tower):
    name = "Tower11"
    image = images.Tower11
    upgrades = []

    def attack(self, target):
        direction = target.towards(self.x, self.y)
        rot = get_rotation_norm(*direction)
        self.sprite.rotation = 90 - rot * 180 / math.pi
        for i in range(int(self.stats["shots"])):
            Bullet(self.x, self.y, rot + self.stats["spread"] * math.sin(self.game.ticks + 5 * i), self.game, self.side,
                   self.stats["dmg"], self, self.stats["bulletspeed"],
                   self.stats["reach"] * 1.5, scale=self.stats["bullet_scale"])


class Tower3(tower_upgrade, Tower):
    name = "Tower3"
    image = images.Tower3
    upgrades = []

    def attack(self, target):
        direction = target.towards(self.x, self.y)
        self.sprite.rotation = 90 - get_rotation_norm(*direction) * 180 / math.pi
        Arrow(self.x, self.y, *direction, self.game, self.side, self.stats["dmg"], self, self.stats["bulletspeed"],
              self.stats["reach"], scale=self.stats["bullet_scale"], pierce=self.stats["pierce"],
              cluster=self.stats["cluster"], recursion=self.stats["recursion"])


class Tower31(tower_upgrade, Tower):
    name = "Tower31"
    image = images.Tower31
    upgrades = []

    def attack(self, target):
        direction = target.towards(self.x, self.y)
        self.sprite.rotation = 90 - get_rotation_norm(*direction) * 180 / math.pi
        Arrow(self.x, self.y, *direction, self.game, self.side, self.stats["dmg"], self, self.stats["bulletspeed"],
              self.stats["reach"], scale=self.stats["bullet_scale"], pierce=self.stats["pierce"],
              cluster=self.stats["cluster"], recursion=self.stats["recursion"])


class Farm(Building):
    name = "Farm"
    entity_type = "farm"
    image = images.Farm
    upgrades = []

    def __init__(self, x, y, tick, side, game):
        game.players[side].force_purchase(self.get_cost([]))
        super().__init__(x, y, tick, side, game)
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


class farm_upgrade(Farm):
    upgrades = []
    name = "Farm"

    def __init__(self, target=None, tick=None, x=None, y=None, side=None, game=None, ID=None):
        if target is not None:
            super().__init__(target.x, target.y, tick, target.side, target.game)
            self.comes_from = target
            self.ID = target.ID
        else:
            super().__init__(x, y, tick, side, game)
            self.comes_from = None
            self.ID = ID
        self.upgrades_into = [e for e in self.upgrades]

    @classmethod
    def get_cost(cls, params=()):
        resources = {"money": unit_stats[cls.name]["cost"]}
        for e in unit_stats[cls.name].keys():
            if e.startswith("cost_"):
                resources[e[5::]] = unit_stats[cls.name][e]
        return resources


class Farm1(farm_upgrade, Farm):
    name = "Farm1"
    image = images.Farm1
    upgrades = []


class Farm11(farm_upgrade, Farm):
    name = "Farm11"
    image = images.Farm11
    upgrades = []


class Farm2(farm_upgrade, Farm):
    name = "Farm2"
    image = images.Farm2
    upgrades = []


class Farm21(farm_upgrade, Farm):
    name = "Farm21"
    image = images.Farm21
    upgrades = []

    def __init__(self, target=None, tick=None, x=None, y=None, side=None, game=None, ID=None):
        super().__init__(target, tick, x, y, side, game, ID)
        self.additionals = []

    def on_summon(self):
        self.additionals.append(
            aura(effect_combined,
                 (
                     (effect_stat_mult, effect_stat_mult, effect_stat_add, effect_visual),
                     (
                         ("speed", self.stats["buff"]),
                         ("dmg", self.stats["buff"]),
                         ("health", self.stats["health_buff"]),
                         (images.Glow, 150, 1.5)
                     ),
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

    def __init__(self, x1, y1, x2, y2, tick, side, game):
        game.players[side].force_purchase(self.get_cost([]))
        self.exists = False
        self.spawning = game.ticks - tick
        self.ID = (x1, y1, tick)
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.x, self.y = (x1 + x2) / 2, (y1 + y2) / 2
        self.length = ((self.x1 - self.x2) ** 2 + (self.y1 - self.y2) ** 2) ** .5
        self.norm_vector = ((self.y2 - self.y1) / self.length, (self.x1 - self.x2) / self.length)
        self.line_c = -self.norm_vector[0] * self.x1 - self.norm_vector[1] * self.y1
        self.crossline_c = (-self.norm_vector[1] * (self.x1 + self.x2) + self.norm_vector[0] * (self.y1 + self.y2)) * .5
        self.side = side
        self.width = unit_stats[self.name]["size"]
        self.game = game
        game.players[side].walls.append(self)

        self.chunks = get_wall_chunks(self.x1, self.y1, self.x2, self.y2, self.norm_vector, self.line_c, self.width)
        for e in self.chunks:
            self.game.add_wall_to_chunk(self, e)
        self.collision_chunks = []
        for c in self.chunks:
            self.collision_chunks.append(self.game.chunks[c])

        x = self.width * .5 / self.length
        a = x * (self.y2 - self.y1)
        b = x * (self.x1 - self.x2)
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        self.vertices_no_cam = [e * SPRITE_SIZE_MULT for e in [
            self.x1 - a, self.y1 - b, self.x1 + a, self.y1 + b, self.x2 + a, self.y2 + b, self.x2 - a, self.y2 - b]]
        self.sprite = game.batch.add(
            4, pyglet.gl.GL_QUADS, client_utility.wall_group,
            ("v2f", self.vertices_no_cam),
            ("t2f", (0, 0, 1, 0, 1, 0.5 / x,
                     0, 0.5 / x)),
            ("c4B", (255, 255, 255, 70) * 4)
        )
        self.crack_sprite = game.batch.add(
            4, pyglet.gl.GL_QUADS, client_utility.wall_crack_group,
            ("v2f", self.vertices_no_cam),
            ("t2f", (0, 0, 1, 0, 1, 0.25 / x,
                     0, 0.25 / x)),
            ("c4B", (255, 255, 255, 0) * 4)
        )
        self.update_cam(self.game.camx, self.game.camy)
        self.effects = []
        self.base_stats = unit_stats[self.name]
        self.mods_add = {e: [] for e in unit_stats[self.name].keys()}
        self.mods_multiply = {e: [] for e in unit_stats[self.name].keys()}
        self.stats = {e: (self.base_stats[e] + sum(self.mods_add[e])) * product(*self.mods_multiply[e]) for e in
                      self.base_stats.keys()}
        self.health = self.stats["health"]
        self.frozen = 0
        game.players[side].on_building_summon(self)

    @classmethod
    def get_cost(cls, params=()):
        resources = {"money": unit_stats[cls.name]["cost"]}
        for e in unit_stats[cls.name].keys():
            if e.startswith("cost_"):
                resources[e[5::]] = unit_stats[cls.name][e]
        return resources

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

    def die(self):
        if not self.exists:
            return
        self.sprite.delete()
        self.crack_sprite.delete()
        self.game.players[self.side].walls.remove(self)
        [self.game.remove_wall_from_chunk(self, e) for e in self.chunks]
        self.exists = False
        while self.effects:
            self.effects[0].on_death()
            self.effects[0].remove()

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
                    continue
                if point_line_dist(e.x, e.y, self.norm_vector, self.line_c) < (self.width + e.size) * .5 and \
                        point_line_dist(e.x, e.y, (self.norm_vector[1], -self.norm_vector[0]),
                                        self.crossline_c) < self.length * .5:
                    shovage = point_line_dist(e.x, e.y, self.norm_vector, self.line_c) - (self.width + e.size) * .5
                    if e.x * self.norm_vector[0] + e.y * self.norm_vector[1] + self.line_c > 0:
                        shovage *= -1
                    e.take_knockback(self.norm_vector[0] * shovage, self.norm_vector[1] * shovage, self)

    def update_cam(self, x, y):
        self.sprite.vertices = self.crack_sprite.vertices = [(self.vertices_no_cam[i] - (x if i % 2 == 0 else y)) for i
                                                             in range(8)]

    def tick(self):
        if self.spawning < FPS * ACTION_DELAY:
            self.spawning += 1
        if self.spawning >= FPS * ACTION_DELAY:
            self.exists = True
            self.sprite.colors = (255,) * 16
            self.tick = self.tick2
            self.update_stats()

    def tick2(self):
        self.shove()
        [e.tick() for e in self.effects]

    def graphics_update(self, dt):
        self.crack_sprite.colors[3::4] = [int((255 * (self.stats["health"] - self.health)) // self.stats["health"])] * 4
        [e.graphics_update(dt) for e in self.effects]


class Formation:
    def __init__(self, instructions, troops, tick, side, game, x=None, y=None, AI=False, amplifier=1.0):
        self.game = game
        self.spawning = game.ticks - tick
        self.ID = (game.ticks - self.spawning,)
        if x is None:
            self.x, self.y = game.players[side].TownHall.x, game.players[side].TownHall.y
        else:
            self.x, self.y = x, y
        if not AI:
            game.players[side].force_purchase(self.get_cost(troops))
            self.has_warning = False
            self.warning = None
        elif side != game.side:
            self.has_warning = True
            warn_angle = get_rotation(self.x * SPRITE_SIZE_MULT - game.camx - SCREEN_WIDTH / 2,
                                      self.y * SPRITE_SIZE_MULT - game.camy - SCREEN_HEIGHT / 2)
            self.warning = pyglet.sprite.Sprite(images.Warn, x=SCREEN_WIDTH / 2 + 500 * math.cos(warn_angle),
                                                y=SCREEN_HEIGHT / 2 + 500 * math.sin(warn_angle), batch=game.batch,
                                                group=groups.g[15])
            self.warning.scale = 0.2 * SPRITE_SIZE_MULT
        else:
            self.has_warning = False
            self.warning = None
        self.warn_opacity = 255
        self.AI = AI
        self.entity_type = "formation"
        self.exists = False
        self.instructions = instructions
        self.side = side
        self.troops = []
        self.game.players[self.side].formations.append(self)
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
        if self.has_warning:
            self.warning.delete()

    def update_cam(self, x, y):
        [e.update_cam(x, y) for e in self.troops]
        if self.has_warning:
            self.update_warning(x, y)

    def update_warning(self, x, y):
        self.warn_opacity = max(0, self.warn_opacity-1)
        warn_distance = 350
        dist = hypot(self.x * SPRITE_SIZE_MULT - x - SCREEN_WIDTH / 2,
                     self.y * SPRITE_SIZE_MULT - y - SCREEN_HEIGHT / 2)
        if dist > warn_distance:
            warn_angle = get_rotation(self.x * SPRITE_SIZE_MULT - x - SCREEN_WIDTH / 2,
                                      self.y * SPRITE_SIZE_MULT - y - SCREEN_HEIGHT / 2)
            self.warning.update(x=SCREEN_WIDTH / 2 + warn_distance * math.cos(warn_angle),
                                y=SCREEN_HEIGHT / 2 + warn_distance * math.sin(warn_angle))
        else:
            self.warning.update(x=self.x * SPRITE_SIZE_MULT - x,
                                y=self.y * SPRITE_SIZE_MULT - y)
        if self.warning.opacity > 0:
            self.warning.opacity = self.warn_opacity
        else:
            self.warning.delete()
            self.has_warning = False

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
    image = images.Cancelbutton
    name = "None"

    def __init__(self, ID, x, y, side, column, row, game: Game, formation: Formation, effects=()):
        self.sounds = noise.sounds[self.name]
        self.entity_type = "unit"
        self.last_camx, self.last_camy = game.camx, game.camy
        self.ID = ID
        self.lifetime = 0
        self.side = side
        self.game = game
        self.wait_for_this = True
        self.formation = formation
        self.x, self.y = x, y
        self.flying = False
        self.shown = True
        self.last_x, self.last_y = x, y
        self.column, self.row = column, row
        self.game.players[self.side].units.append(self)
        self.size = unit_stats[self.name]["size"]
        self.sprite = client_utility.sprite_with_scale(self.image, unit_stats[self.name][
            "vwidth"] * SPRITE_SIZE_MULT / self.image.width,
                                                       1, 1, batch=game.batch, x=x * SPRITE_SIZE_MULT - game.camx,
                                                       y=y * SPRITE_SIZE_MULT - game.camy, group=groups.g[5])
        hpbar_y_centre = self.sprite.y
        hpbar_y_range = 1.5 * SPRITE_SIZE_MULT
        hpbar_x_centre = self.sprite.x
        hpbar_x_range = self.size * SPRITE_SIZE_MULT / 2
        self.hpbar = game.batch.add(
            8, pyglet.gl.GL_QUADS, groups.g[7],
            ("v2f", (hpbar_x_centre - hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre - hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range)),
            ("c3B/static", (0, 255, 0, 0, 255, 0, 0, 255, 0, 0, 255, 0, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50)
            if self.game.side == self.side else (
                163, 73, 163, 163, 73, 163, 163, 73, 163, 163, 73, 163, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50))
        )

        self.current_cooldown = 0
        self.sprite.opacity = 70
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
        self.recent_target = None
        for e in effects:
            e.apply(self)
        # self.TESTING_t1=0
        # self.TESTING_t2 = 0
        # self.TESTING_t3 = 0

    def show(self):
        self.sprite.batch = self.game.batch
        [e.graphics_show() for e in self.effects]
        self.shown = True

    def hide(self):
        self.sprite.batch = None
        [e.graphics_hide() for e in self.effects]
        self.shown = False

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
        self.sprite.scale = self.stats["vwidth"] * SPRITE_SIZE_MULT / self.image.width

    def distance_to_point(self, x, y):
        return distance(self.x, self.y, x, y) - self.size / 2

    def fast_point_dist(self, x, y):
        return abs(self.x - x) + abs(self.y - y) - self.size / 2

    def towards(self, x, y):
        dx, dy = self.x - x, self.y - y
        invh = inv_h(dx, dy)
        return dx * invh, dy * invh

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

    @classmethod
    def get_cost(cls, params=()):
        resources = {"money": unit_stats[cls.name]["cost"]}
        for e in unit_stats[cls.name].keys():
            if e.startswith("cost_"):
                resources[e[5::]] = unit_stats[cls.name][e]
        return resources

    def update_hpbar(self):
        if not self.exists:
            return
        hpbar_y_centre = self.sprite.y
        hpbar_y_range = 2 * SPRITE_SIZE_MULT
        hpbar_x_centre = self.sprite.x
        hpbar_x_range = self.size * SPRITE_SIZE_MULT / 2
        health_size = hpbar_x_range * (2 * self.health / self.stats["health"] - 1)
        self.hpbar.vertices = (hpbar_x_centre - hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                               hpbar_x_centre - hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre - hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre - hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range)

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
            return d <= self.stats["reach"] + self.size
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
            noise.play(self.name, "attack")
            self.attack(target)

    def attack(self, target):
        pass

    def tick(self):
        self.recent_target = None
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
                    self.recent_target = self.target

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
        self.last_x, self.last_y = self.x, self.y
        [e.tick() for e in self.effects]

    def die(self):
        if not self.exists:
            return
        self.formation.troops.remove(self)
        self.game.players[self.side].units.remove(self)
        self.sprite.delete()
        self.hpbar.delete()
        if not self.formation.troops:
            self.formation.delete()
        self.formation = None
        self.exists = False
        while self.effects:
            self.effects[0].on_death()
            self.effects[0].remove()
        noise.play(self.name, "die")

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

    def rotate(self, x, y):
        if x == y == 0:
            return
        inv_hypot = inv_h(x, y)
        r = get_rotation(x, y)
        self.rotation = r
        self.vx, self.vy = x * inv_hypot * self.stats["speed"], y * inv_hypot * self.stats["speed"]

    def summon_done(self):
        self.exists = True
        self.sprite.opacity = 255
        self.game.players[self.side].on_unit_summon(self)
        self.update_stats()
        noise.play(self.name, "spawn")

    def update_cam(self, x, y):
        return

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

    def graphics_update(self, dt):
        if not self.exists:
            return
        x, y = self.x * SPRITE_SIZE_MULT - self.game.camx, self.y * SPRITE_SIZE_MULT - self.game.camy
        if self.shown:
            self.sprite.update(x=x, y=y, rotation=(-self.rotation * 180 / math.pi + 90) if self.recent_target is None
            else -get_rotation(self.recent_target.x - self.x,
                               self.recent_target.y - self.y) * 180 / math.pi + 90)
            [e.graphics_update(dt) for e in self.effects]
            self.update_hpbar()
            if x + self.size < 0 or x - self.size > SCREEN_WIDTH or y + self.size < 0 or y - self.size > SCREEN_HEIGHT:
                self.hide()
                return
        elif x + self.size > 0 and x - self.size < SCREEN_WIDTH and y + self.size > 0 and y - self.size < SCREEN_HEIGHT:
            self.show()

    @classmethod
    def get_image(cls):
        return [cls.image, unit_stats[cls.name]["vwidth"] * SPRITE_SIZE_MULT / cls.image.width, 1, 1]


class Swordsman(Unit):
    image = images.Swordsman
    name = "Swordsman"

    def attack(self, target):
        target.take_damage(self.stats["dmg"], self)


class selection_swordsman(selection_unit):
    img = images.Swordsman
    unit_num = 0


class Archer(Unit):
    image = images.Bowman
    name = "Archer"

    def attack(self, target):
        Arrow(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"], self,
              self.stats["bulletspeed"],
              self.stats["reach"] * 1.5,
              scale=self.stats["bullet_scale"], pierce=self.stats["pierce"], cluster=self.stats["cluster"],
              recursion=self.stats["recursion"])


class selection_archer(selection_unit):
    img = images.Bowman
    unit_num = 1


class Trebuchet(Unit):
    image = images.Trebuchet
    name = "Trebuchet"

    def attack(self, target):
        Boulder(self.x, self.y, *target.towards(self.x, self.y), self.game, self.side, self.stats["dmg"], self,
                self.stats["bulletspeed"],
                max(self.stats["min_range"], target.distance_to_point(self.x, self.y)), self.stats["explosion_radius"],
                scale=self.stats["bullet_scale"], pierce=self.stats["pierce"], cluster=self.stats["cluster"],
                recursion=self.stats["recursion"])


class Defender(Unit):
    image = images.Defender
    name = "Defender"

    def attack(self, target):
        target.take_damage(self.stats["dmg"], self)


class Mancatcher(Unit):
    image = images.Mancatcher
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
    image = images.Bear
    name = "Bear"

    def attack(self, target):
        target.take_damage(self.stats["dmg"], self)


class Necromancer(Unit):
    image = images.Necromancer
    name = "Necromancer"
    beam_half_width = 20

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attack_animation = self.game.batch.add(
            4, pyglet.gl.GL_QUADS, client_utility.necro_beam_group,
            ("v2f", (0, 0, 0, 0, 0, 0, 0, 0)),
            ("t2f", (0, 0, 0, 0, 0, 0, 0, 0)),
            ("c4B", (255, 255, 255, 255) * 4)
        )
        self.beam_var = 0
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        self.zombies = 0

    def tick(self):
        self.attack_animation.colors[3::4] = [max(0, self.attack_animation.colors[3] - 20)] * 4
        super().tick()

    def aim_beam(self, x, y):
        self.attack_animation.colors[3::4] = [255] * 4
        x1, y1 = (self.x - self.game.camx) * SPRITE_SIZE_MULT, (self.y - self.game.camy) * SPRITE_SIZE_MULT
        x2, y2 = (x - self.game.camx) * SPRITE_SIZE_MULT, (y - self.game.camy) * SPRITE_SIZE_MULT
        dx, dy = x2 - x1, y2 - y1
        inv_length = inv_h(x1 - x2, y1 - y2)
        length = distance(x1, y1, x2, y2)
        norm_x, norm_y = dx * inv_length, dy * inv_length
        self.attack_animation.vertices = (
            x1 + norm_y * self.beam_half_width, y1 - norm_x * self.beam_half_width,
            x2 + norm_y * self.beam_half_width, y2 - norm_x * self.beam_half_width,
            x2 - norm_y * self.beam_half_width, y2 + norm_x * self.beam_half_width,
            x1 - norm_y * self.beam_half_width, y1 + norm_x * self.beam_half_width,
        )
        self.attack_animation.tex_coords = (1, self.beam_var, 1,
                                            length / images.Beam.height + self.beam_var,
                                            0, length / images.Beam.height + self.beam_var,
                                            0, self.beam_var)
        self.beam_var += 0.015

    def attack(self, target):
        if target.entity_type != "wall":
            self.aim_beam(target.x, target.y)
        else:
            self.aim_beam((target.x1 + target.x2) / 2, (target.y1 + target.y2) / 2)
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
                            effect_stat_add("vwidth", e.base_stats["vwidth"] - 20),
                            effect_stat_add("cd", e.base_stats["cd"] / self.stats["steal"])
                            )
                   )
        a.summon_done()
        self.formation.troops.append(a)
        self.zombies += 1

    def die(self):
        super().die()
        self.attack_animation.delete()


class Zombie(Unit):
    image = images.Zombie
    name = "Zombie"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.zombies = 0
        self.wait_for_this = False

    def attack(self, target):
        assert target.exists
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
                            effect_stat_add("vwidth", e.base_stats["vwidth"] - 20),
                            effect_stat_add("cd", e.base_stats["cd"] / self.stats["steal"])
                            )
                   )
        a.summon_done()
        self.formation.troops.append(a)
        self.zombies += 1


class Golem(Unit):
    image = images.Golem
    name = "Golem"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.eaten_tower = 0
        self.tower_sprite = None

    def attack(self, target):
        if target.entity_type == "tower" and target.health > self.eaten_tower:
            self.eaten_tower = target.health
            self.tower_sprite = pyglet.sprite.Sprite(target.image, self.sprite.x, self.sprite.y,
                                                     batch=self.game.batch, group=groups.g[6])
            self.tower_sprite.rotation = self.sprite.rotation
            self.tower_sprite.scale = target.size / self.tower_sprite.width
            target.die()
            return
        elif target.entity_type == "wall":
            target.take_damage(self.stats["wall_mult"] * (self.stats["dmg"] + self.eaten_tower), self)
        else:
            target.take_damage(self.stats["dmg"] + self.eaten_tower, self)

    def graphics_update(self, dt):
        super().graphics_update(dt)
        if self.tower_sprite is not None and self.shown:
            self.tower_sprite.update(x=self.sprite.x, y=self.sprite.y, rotation=self.sprite.rotation)

    def die(self):
        if self.tower_sprite is not None:
            self.tower_sprite.delete()
        super().die()


class selection_trebuchet(selection_unit):
    img = images.Trebuchet
    unit_num = 2


class selection_defender(selection_unit):
    img = images.Defender
    unit_num = 3


class selection_bear(selection_unit):
    img = images.Bear
    unit_num = 4


class selection_necromancer(selection_unit):
    img = images.Necromancer
    unit_num = 5


class selection_golem(selection_unit):
    img = images.Golem
    unit_num = 7


class selection_mancatcher(selection_unit):
    img = images.Mancatcher
    unit_num = 8


possible_units = [Swordsman, Archer, Trebuchet, Defender, Bear, Necromancer, Zombie, Golem, Mancatcher]
selects_p1 = [selection_tower, selection_wall, selection_farm]
selects_p2 = [selection_swordsman, selection_archer, selection_mancatcher, selection_trebuchet, selection_defender,
              selection_bear, selection_necromancer, selection_golem]
selects_p3 = [selection_fireball, selection_freeze, selection_rage, selection_tree]
selects_all = [selects_p1, selects_p2, selects_p3]


class Projectile:
    image = images.Bullet
    scale = 1

    def __init__(self, x, y, dx, dy, game, side, damage, source, speed, reach, scale=None, pierce=2, cluster=5,
                 rotation=None, recursion=2, animated=False):
        # (dx,dy) must be normalizedas
        self.x, self.y = x, y
        self.animated = animated
        if animated:
            self.sprite = client_utility.animation(self.x, self.y,
                                                   self.scale if scale is None else scale, game, img=self.image,
                                                   duration=reach / speed * constants.INV_FPS)
        else:
            self.sprite = pyglet.sprite.Sprite(self.image, self.x, self.y, batch=game.batch, group=groups.g[5])
            if scale is None:
                self.sprite.scale = self.scale * SPRITE_SIZE_MULT
            else:
                self.sprite.scale = scale * SPRITE_SIZE_MULT
        if rotation is None:
            rotation = get_rotation_norm(dx, dy)
        self.sprite.rotation = 90 - rotation * 180 / math.pi
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
        self.sprite.delete()
        self.already_hit = []

    def graphics_update(self, dt):
        if self.animated:
            self.sprite.true_x = self.x
            self.sprite.true_y = self.y
            self.sprite.tick(dt)
        else:
            self.sprite.update(x=self.x * SPRITE_SIZE_MULT - self.game.camx,
                               y=self.y * SPRITE_SIZE_MULT - self.game.camy)

    def split(self):
        if self.recursion > 0:
            for i in range(self.cluster):
                self.__class__(self.x, self.y, 0, 0, self.game, self.side, self.damage, self.source, self.speed,
                               self.max_reach * RECURSION_REACH,
                               scale=self.sprite.scale / SPRITE_SIZE_MULT, pierce=self.max_pierce,
                               cluster=self.cluster, rotation=self.game.ticks + 2 * math.pi * i / self.cluster,
                               recursion=self.recursion - 1)


class Projectile_with_size(Projectile):
    def __init__(self, x, y, dx, dy, game, side, damage, source, speed, reach, size, scale=None, pierce=2, cluster=5,
                 rotation=None, recursion=2, animated=False):
        super().__init__(x, y, dx, dy, game, side, damage, source, speed, reach, scale=scale, pierce=pierce,
                         cluster=cluster, rotation=rotation, recursion=2, animated=animated)
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


class Arrow(Projectile):
    image = images.Arrow
    scale = .1

    def __init__(self, x, y, dx, dy, game, side, damage, source, speed, reach, scale=None, pierce=2, cluster=5,
                 rotation=None, recursion=2, animated=False):
        super().__init__(x, y, dx, dy, game, side, damage, source, speed, reach, scale, pierce, cluster, rotation,
                         recursion, animated)


class flame_wave(Projectile_with_size):
    image = images.flame_wave
    scale = 80

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, animated=True)


class Boulder(Projectile):
    image = images.Boulder
    scale = .15

    def __init__(self, x, y, dx, dy, game, side, damage, source, speed, reach, radius, scale=None, pierce=2, cluster=5,
                 rotation=None, recursion=1):
        super().__init__(x, y, dx, dy, game, side, damage, source, speed, reach, scale, pierce, cluster, rotation,
                         recursion)
        self.radius = radius
        self.rotation_speed = (random.random() - .5) * 10

    def tick(self):
        self.x += self.vx
        self.y += self.vy
        self.reach -= self.speed
        if self.reach <= 0:
            self.explode()

    def explode(self):
        AOE_damage(self.x, self.y, self.radius, self.damage, self.source, self.game)
        animation_explosion(self.x, self.y, self.radius, 100, self.game)
        self.delete()

    def graphics_update(self, dt):
        super().graphics_update(dt)
        self.sprite.rotation += self.rotation_speed

    def split(self):
        if self.recursion > 0:
            for i in range(self.cluster):
                self.__class__(self.x, self.y, 0, 0, self.game, self.side, self.damage, self.source, self.speed,
                               self.max_reach * RECURSION_REACH,
                               self.radius, self.sprite.scale / SPRITE_SIZE_MULT, self.max_pierce,
                               self.cluster,
                               self.game.ticks + 2 * math.pi * i / self.cluster,
                               self.recursion - 1)


class Mine(Boulder):
    image = images.Mine

    def __init__(self, x, y, dx, dy, game, side, damage, source, speed, reach, radius, lifetime, scale=None, pierce=2,
                 cluster=5, recursion=1):
        d = inv_h(dx, dy)
        super().__init__(x, y, dx * d, dy * d, game, side, damage, source, speed, reach, radius, scale, pierce, cluster,
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
                self.rotation_speed = 0
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


class Meteor(Projectile):
    image = images.Meteor
    scale = .15

    def __init__(self, x, y, dx, dy, game, side, damage, source, speed, reach, radius, scale=None, pierce=2, cluster=5,
                 rotation=None, recursion=2):
        super().__init__(x, y, dx, dy, game, side, damage, source, speed, reach, scale, pierce, cluster, rotation,
                         recursion)
        self.radius = radius

    def tick(self):
        self.x += self.vx
        self.y += self.vy
        self.reach -= self.speed
        if self.reach <= 0:
            self.explode()

    def explode(self):
        AOE_damage(self.x, self.y, self.radius, self.damage, self.source, self.game)
        animation_explosion(self.x, self.y, self.radius, 100, self.game)
        self.delete()

    def graphics_update(self, dt):
        super().graphics_update(dt)

    def split(self):
        if self.recursion > 0:
            for i in range(self.cluster):
                self.__class__(self.x, self.y, 0, 0, self.game, self.side, self.damage, self.source, self.speed,
                               self.max_reach * RECURSION_REACH,
                               self.radius, self.sprite.scale / SPRITE_SIZE_MULT, self.max_pierce,
                               self.cluster,
                               self.game.ticks + 2 * math.pi * i / self.cluster,
                               self.recursion - 1)


class Egg(Meteor):
    image = images.Egg
    scale = .15
    explosion_size = 80
    explosion_speed = 100

    def explode(self):
        AOE_damage(self.x, self.y, self.radius, self.damage, self.source, self.game)
        animation_explosion(self.x, self.y, self.radius / 2, 300, self.game)
        self.delete()


class animation_explosion:
    def __init__(self, x, y, size, speed, game):
        if len(game.animations) > MAX_ANIMATIONS:
            return
        image = random.choice(
            [images.Explosion, images.Explosion1, images.Explosion2]) if size < 500 else images.Explosion
        self.sprite = client_utility.animation(x, y, size, game, image, group=7 + math.floor(size / 500))
        self.sprite2 = pyglet.sprite.Sprite(images.Shockwave, x=x * SPRITE_SIZE_MULT - game.camx,
                                            y=y * SPRITE_SIZE_MULT - game.camy,
                                            batch=game.batch, group=groups.g[6])
        self.sprite_duration = image.get_duration()
        self.sprite.rotation = random.randint(0, 360)
        self.x, self.y = x, y
        self.game = game
        self.size, self.speed = size, speed
        self.exists_time = 0
        game.animations.append(self)
        if size > 100:
            animation_crater(x, y, size / 2, size / 3, game)
        self.exists = True
        self.duration = 128 / speed
        self.explosion_speed = 2 / self.duration
        if size > 500:
            animation_screen_shake(size / 200, self.duration * 1.1, self.game)
        self.shockwave_scale_constant = self.size / images.Shockwave.width * 4

    def tick(self, dt):
        self.exists_time += dt
        if self.exists_time > self.duration or dt > .5:
            self.delete()
            return
        if self.sprite._vertex_list is not None:
            self.sprite.update(x=self.x * SPRITE_SIZE_MULT - self.game.camx,
                               y=self.y * SPRITE_SIZE_MULT - self.game.camy,
                               scale=min(.004, self.exists_time * 20 / images.Fire.width) * self.size)
            self.sprite.tick(dt * self.explosion_speed)
        self.sprite2.update(x=self.x * SPRITE_SIZE_MULT - self.game.camx, y=self.y * SPRITE_SIZE_MULT - self.game.camy,
                            scale=self.exists_time * self.shockwave_scale_constant)
        self.sprite2.opacity = 150 * (self.duration - self.exists_time) / self.duration

    def delete(self):
        if not self.exists:
            return
        self.exists = False
        self.game.animations.remove(self)
        self.sprite.delete()
        self.sprite2.delete()


class animation_screen_shake:
    def __init__(self, size, duration, game):
        self.size = size
        self.duration = duration
        self.exists_time = 0
        self.exists = True
        self.game = game
        self.game.animations.append(self)

    def tick(self, dt):
        self.exists_time += dt
        if self.exists_time > self.duration:
            self.delete()
            return
        self.game.camx += self.size * math.sin(self.game.ticks * dt * 100)
        self.game.camy += self.size * math.sin(self.game.ticks * dt * 112)

    def delete(self):
        if not self.exists:
            return
        self.exists = False
        self.game.animations.remove(self)


class animation_crater:
    def __init__(self, x, y, size, duration, game):
        if len(game.animations) > MAX_ANIMATIONS:
            return
        self.sprite = pyglet.sprite.Sprite(images.Crater, x=x * SPRITE_SIZE_MULT - game.camx,
                                           y=y * SPRITE_SIZE_MULT - game.camy,
                                           batch=game.batch, group=groups.g[1])
        self.sprite.rotation = random.randint(0, 360)
        self.sprite.scale = size / self.sprite.width
        self.x, self.y = x, y
        self.game = game
        self.size, self.duration = size, duration
        self.exists_time = 0
        game.animations.append(self)
        self.exists = True

    def tick(self, dt):
        if dt > .5:
            self.delete()
            return
        self.exists_time += dt
        if self.exists_time > self.duration:
            self.delete()
            return
        self.sprite.update(x=self.x * SPRITE_SIZE_MULT - self.game.camx, y=self.y * SPRITE_SIZE_MULT - self.game.camy)
        if self.duration - self.exists_time <= 3:
            self.sprite.opacity = 255 * (self.duration - self.exists_time) // 3

    def delete(self):
        if not self.exists:
            return
        self.exists = False
        self.game.animations.remove(self)
        self.sprite.delete()


class animation_freeze:
    def __init__(self, x, y, size, duration, game):
        if len(game.animations) > MAX_ANIMATIONS:
            return
        self.sprite = pyglet.sprite.Sprite(images.Freeze, x=x * SPRITE_SIZE_MULT - game.camx,
                                           y=y * SPRITE_SIZE_MULT - game.camy,
                                           batch=game.batch, group=groups.g[2])
        self.sprite.rotation = random.randint(0, 360)
        self.sprite.scale = size / self.sprite.width
        self.x, self.y = x, y
        self.game = game
        self.size, self.duration = size, duration
        self.exists_time = 0
        game.animations.append(self)
        self.exists = True

    def tick(self, dt):
        if dt > .1:
            self.delete()
            return
        if self.exists_time >= self.duration:
            self.delete()
            return
        else:
            self.sprite.opacity = 100 * (self.duration - self.exists_time) / self.duration
            self.sprite.update(x=self.x * SPRITE_SIZE_MULT - self.game.camx,
                               y=self.y * SPRITE_SIZE_MULT - self.game.camy)
            self.exists_time += dt

    def delete(self):
        if not self.exists:
            return
        self.exists = False
        self.game.animations.remove(self)
        self.sprite.delete()


class animation_ring_of_fire(client_utility.animation):
    img = images.Explosion1
    standalone = True
    layer = 5


class animation_rage:
    def __init__(self, x, y, size, duration, game):
        if len(game.animations) > MAX_ANIMATIONS:
            return
        self.sprite = pyglet.sprite.Sprite(images.Rage, x=x * SPRITE_SIZE_MULT - game.camx,
                                           y=y * SPRITE_SIZE_MULT - game.camy,
                                           batch=game.batch, group=groups.g[2])
        self.sprite.rotation = random.randint(0, 360)
        self.sprite.scale = size / self.sprite.width
        self.x, self.y = x, y
        self.game = game
        self.size, self.duration = size, duration
        self.exists_time = 0
        game.animations.append(self)
        self.flicker = 100
        self.exists = True

    def tick(self, dt):
        if self.exists_time >= self.duration:
            self.delete()
            return
        else:
            self.sprite.opacity = 255 * (self.duration - self.exists_time) / self.duration \
                                  * abs(math.sin(self.exists_time * 10))
            self.sprite.update(x=self.x * SPRITE_SIZE_MULT - self.game.camx,
                               y=self.y * SPRITE_SIZE_MULT - self.game.camy)
            self.exists_time += dt

    def delete(self):
        if not self.exists:
            return
        self.exists = False
        self.game.animations.remove(self)
        self.sprite.delete()


class animation_frost:
    def __init__(self, x, y, size, duration, game, opacity=255, image=None):
        if len(game.animations) > MAX_ANIMATIONS:
            return
        self.max_opacity = opacity
        self.sprite = pyglet.sprite.Sprite(images.Freeze if image is None else image,
                                           x=x * SPRITE_SIZE_MULT - game.camx,
                                           y=y * SPRITE_SIZE_MULT - game.camy,
                                           batch=game.batch, group=groups.g[3])
        self.sprite.rotation = random.randint(0, 360)
        self.sprite.scale = size / self.sprite.width
        self.x, self.y = x, y
        self.game = game
        self.size, self.duration = size, duration
        self.exists_time = 0
        game.animations.append(self)
        self.flicker = .5
        self.exists = True

    def tick(self, dt):
        if dt > .5:
            self.delete()
            return
        if self.duration is not None and self.exists_time >= self.duration:
            self.delete()
            return
        else:
            self.sprite.opacity = self.max_opacity * (.65 + .35 * math.sin(self.exists_time * self.flicker))
            self.sprite.update(x=self.x * SPRITE_SIZE_MULT - self.game.camx,
                               y=self.y * SPRITE_SIZE_MULT - self.game.camy)
            self.exists_time += dt

    def delete(self):
        if not self.exists:
            return
        self.exists = False
        self.game.animations.remove(self)
        self.sprite.delete()


class Bullet(Projectile):
    image = images.Boulder
    scale = .035

    def __init__(self, x, y, angle, game, side, damage, source, speed, reach, scale=None, pierce=1, cluster=0,
                 recursion=0):
        super().__init__(x, y, 0, 0, game, side, damage, source, speed, reach, scale, pierce, cluster, angle, recursion)


def AOE_damage(x, y, size, amount, source, game, type=None):
    chunks_affected = get_chunks(x, y, size * 2)
    side = source.side
    affected_things = []
    for coord in chunks_affected:
        c = game.find_chunk(coord)
        if c is not None:
            for unit in c.units[1 - side]:
                if unit.exists and unit.distance_to_point(x, y) < size and unit not in affected_things:
                    affected_things.append(unit)
            for unit in c.buildings[1 - side]:
                if unit.exists and unit.distance_to_point(x, y) < size and unit not in affected_things:
                    affected_things.append(unit)
            for wall in c.walls[1 - side]:
                if wall.exists and wall.distance_to_point(x, y) < size and wall not in affected_things:
                    affected_things.append(wall)

    for e in affected_things:
        e.take_damage(amount, source, type)


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

    def graphics_update(self, dt):
        pass

    def graphics_show(self):
        pass

    def graphics_hide(self):
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
        super().__init__(0, ID=None, from_aura=None)
        self.amount = amount

    def apply(self, target):
        target.health = min(target.health + self.amount, target.stats["health"])


class effect_stat_mult(effect):
    def __init__(self, stat, amount, duration=None, ID=None, from_aura=None):
        super().__init__(duration, ID, from_aura)
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


class effect_visual(effect):
    def __init__(self, img, opacity, size, duration=None, ID=None, from_aura=None):
        super().__init__(duration, ID, from_aura)
        self.batch = None
        self.img, self.opacity, self.size = img, opacity, size
        self.sprite = None

    def on_apply(self, target):
        self.batch = target.game.batch
        self.sprite = pyglet.sprite.Sprite(self.img, target.x, target.y,
                                           batch=self.batch if target.shown else None, group=groups.g[1])
        self.sprite.opacity = self.opacity
        self.sprite.scale = self.size / self.img.width * target.size

    def graphics_update(self, dt):
        self.sprite.update(x=self.target.x * SPRITE_SIZE_MULT - self.target.game.camx,
                           y=self.target.y * SPRITE_SIZE_MULT - self.target.game.camy)

    def graphics_show(self):
        self.sprite.batch = self.batch

    def graphics_hide(self):
        self.sprite.batch = None

    def on_remove(self):
        if self.sprite is not None:
            self.sprite.delete()
            self.sprite = None


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
        self.require_1_tag = require_1_tag
        self.args = args
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
            affected = []
            for c in self.chunks:
                ch = self.game.find_chunk(c)
                if ch is not None:
                    for e in ch.units[self.side]:
                        if e.distance_to_point(self.x_y_rad[0], self.x_y_rad[1]) < self.x_y_rad[2]:
                            if e not in affected:
                                affected.append(e)
                    for e in ch.buildings[self.side]:
                        if e.distance_to_point(self.x_y_rad[0], self.x_y_rad[1]) < self.x_y_rad[2]:
                            if e not in affected:
                                affected.append(e)
                    for e in ch.walls[self.side]:
                        if e.distance_to_point(self.x_y_rad[0], self.x_y_rad[1]) < self.x_y_rad[2]:
                            if e not in affected:
                                affected.append(e)
            for e in affected:
                self.apply(e)
        self.apply_counter += 1
        if self.remaining_duration is None:
            return
        self.remaining_duration -= 1
        if self.remaining_duration <= 0:
            self.exists = False

    def delete(self):
        self.exists = False

    def apply(self, target):
        if self.targets is None or has_tags(target.name, self.targets, self.require_1_tag):
            self.effect(*self.args).apply(target)


class Upgrade:
    image = images.Tower
    previous = []
    excludes = []
    name = "This Is A Bug."
    x = 0
    y = 0

    def __init__(self, player, tick):
        player.pending_upgrades.append(self)
        self.time_remaining = float(upgrade_stats[self.name]["time"]) * FPS - player.game.ticks + tick
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
    def attempt_buy(cls, game):
        game.connection.Send({"action": "th upgrade", "num": possible_upgrades.index(cls)})

    @classmethod
    def get_cost(cls, params=()):
        resources = {"money": int(upgrade_stats[cls.name]["cost"])}
        for e in upgrade_stats[cls.name].keys():
            if e.startswith("cost_"):
                resources[e[5::]] = int(upgrade_stats[cls.name][e])
        return resources

    @classmethod
    def get_time(cls):
        return int(upgrade_stats[cls.name]["time"])


class Upgrade_Menu(client_utility.toolbar):
    def __init__(self, game):
        self.batch = game.batch
        super().__init__(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, self.batch, image=images.UpgradeScreen, layer=12)
        self.buttons = []
        game.key_press_detectors.append(self)
        game.mouse_click_detectors.append(self)
        game.mouse_move_detectors.append(self)
        game.drawables.append(self)
        self.game = game
        self.moneylabel = pyglet.text.Label(x=SCREEN_WIDTH * 0.995, y=SCREEN_HEIGHT * 0.995, text="Gold:0",
                                            color=(255, 240, 0, 255),
                                            group=groups.g[15], batch=self.batch, anchor_y="top", anchor_x="right",
                                            font_size=0.01 * SCREEN_WIDTH)
        self.sprites = [self.moneylabel]
        self.movables = []
        self.opened = True
        self.unfinished_upgrades = []
        for e in possible_upgrades:
            self.movables.append(self.add(e.attempt_buy, e.x * 200 * SPRITE_SIZE_MULT + SCREEN_HEIGHT * .75,
                                          e.y * 200 * SPRITE_SIZE_MULT + SCREEN_HEIGHT * .45, SCREEN_HEIGHT * .1,
                                          SCREEN_HEIGHT * .1, e.image, args=(self.game,),
                                          layer=4, mouseover=self.open_desc, mover_args=(e,), mouseoff=self.close_desc))
            for prev in e.previous:
                line = pyglet.sprite.Sprite(images.UpgradeLine,
                                            x=SPRITE_SIZE_MULT * (e.x + prev.x) * 100 + SCREEN_HEIGHT * .8,
                                            y=SPRITE_SIZE_MULT * (e.y + prev.y) * 100 + SCREEN_HEIGHT * .5,
                                            batch=self.batch,
                                            group=groups.g[self.layer + 2])
                line.rotation = 90 - get_rotation(e.x - prev.x, e.y - prev.y) * 180 / math.pi
                line.scale_x = SCREEN_WIDTH * .05 / line.width
                line.scale_y = distance(e.x, e.y, prev.x, prev.y) * 200 * SPRITE_SIZE_MULT / line.height
                self.sprites.append(line)
                self.movables.append(line)
            bg = pyglet.sprite.Sprite(images.UpgradeCircle, x=e.x * 200 * SPRITE_SIZE_MULT + SCREEN_HEIGHT * .8,
                                      y=e.y * 200 * SPRITE_SIZE_MULT + SCREEN_HEIGHT * .5,
                                      batch=self.batch, group=groups.g[self.layer + 2])
            bg.scale = SCREEN_HEIGHT * .12 / bg.height
            bg.opacity = 0
            self.sprites.append(bg)
            self.movables.append(bg)
            self.unfinished_upgrades.append([e, bg])
        self.upgrade_desc = None
        self.x_moving = self.y_moving = 0
        self.keys_pressed = []

    def open_desc(self, upg):
        if self.upgrade_desc is not None and self.upgrade_desc.open:
            self.upgrade_desc.close()
        available = 1
        rem_time = 0
        for e in upg.previous:
            if not self.game.players[self.game.side].has_upgrade(e):
                available = 0
        if self.game.players[self.game.side].is_upgrade_pending(upg):
            available = 2
            rem_time = self.game.players[self.game.side].upgrade_time_remaining(upg)
        elif self.game.players[self.game.side].has_upgrade(upg):
            available = 3
        for e in upg.excludes:
            if self.game.players[self.game.side].has_upgrade(e):
                available = 4
        self.upgrade_desc = upgrade_description(upg, self.batch, self.layer + 4, available, remaining_time=rem_time)

    def close_desc(self):
        if self.upgrade_desc is not None and self.upgrade_desc.open:
            self.upgrade_desc.close()
            self.upgrade_desc = None

    def close(self):
        self.game.key_press_detectors.remove(self)
        self.game.mouse_click_detectors.remove(self)
        self.game.mouse_move_detectors.remove(self)
        self.game.drawables.remove(self)
        self.opened = False
        self.hide()
        self.close_desc()
        for e in self.sprites:
            e.batch = None

    def open(self):
        self.game.key_press_detectors.append(self)
        self.game.mouse_click_detectors.append(self)
        self.game.mouse_move_detectors.append(self)
        self.game.drawables.append(self)
        self.opened = True
        self.show()
        for e in self.sprites:
            e.batch = self.batch

    def key_press(self, symbol, modifiers):
        if symbol not in self.keys_pressed:
            self.keys_pressed.append(symbol)
        if symbol == 65307:
            self.close()
        if symbol in [key.A, key.S, key.D, key.W]:
            self.recalc_camera_movement()

    def recalc_camera_movement(self):
        self.x_moving = (key.D in self.keys_pressed) - (key.A in self.keys_pressed)
        self.y_moving = (key.W in self.keys_pressed) - (key.S in self.keys_pressed)

    def graphics_update(self, dt):
        self.moneylabel.text = "Gold:" + str(int(self.game.players[self.game.side].resources["money"]))
        for e in self.unfinished_upgrades:
            if self.game.players[self.game.side].has_upgrade(e[0]):
                e[1].opacity = 255
                self.unfinished_upgrades.remove(e)
            else:
                remaining = self.game.players[self.game.side].upgrade_time_remaining(e[0])
                if remaining is None:
                    continue
                progress_percent = (e[0].get_time() - remaining * INV_FPS) / e[0].get_time()
                e[1].opacity = progress_percent * 150
        [e.update(e.x - self.x_moving * dt * 500, e.y - self.y_moving * dt * 500) for e in self.movables]
        if self.upgrade_desc is not None and self.upgrade_desc.open:
            self.upgrade_desc.update(dt)

    def key_release(self, symbol, modifiers):
        if symbol in self.keys_pressed:
            self.keys_pressed.remove(symbol)
        if symbol in [key.A, key.S, key.D, key.W]:
            self.recalc_camera_movement()

    def mouse_click(self, x, y, button=0, modifiers=0):
        super().mouse_click(x, y, button, modifiers)

    def mouse_release(self, x, y, button=0, modifiers=0):
        super().mouse_release(x, y, button, modifiers)


class upgrade_description(client_utility.toolbar):
    def __init__(self, upg, batch, layer, available, remaining_time=0):
        super().__init__(SCREEN_WIDTH * .7, 0, SCREEN_WIDTH * .3, SCREEN_HEIGHT, batch, layer=layer)
        self.upg = upg
        self.remaining_time = remaining_time
        self.sprites = []
        if available == 0:
            self.sprites.append(pyglet.text.Label(x=SCREEN_WIDTH * 0.705, y=SCREEN_HEIGHT * 0.01, multiline=True,
                                                  width=SCREEN_WIDTH * .29,
                                                  text="Research previous upgrades first",
                                                  color=(255, 100, 100, 255),
                                                  group=groups.g[layer + 1], batch=batch, anchor_y="bottom",
                                                  anchor_x="left",
                                                  font_size=0.013 * SCREEN_WIDTH))
        elif available == 1:
            self.sprites.append(pyglet.text.Label(x=SCREEN_WIDTH * 0.705, y=SCREEN_HEIGHT * 0.01, multiline=True,
                                                  width=SCREEN_WIDTH * .29,
                                                  text=f"{client_utility.dict_to_string(upg.get_cost())}, Time: {upg.get_time()} sec",
                                                  color=(255, 240, 0, 255),
                                                  group=groups.g[layer + 1], batch=batch, anchor_y="bottom",
                                                  anchor_x="left",
                                                  font_size=0.013 * SCREEN_WIDTH))
        elif available == 2:
            self.sprites.append(pyglet.text.Label(x=SCREEN_WIDTH * 0.705, y=SCREEN_HEIGHT * 0.01, multiline=True,
                                                  width=SCREEN_WIDTH * .29,
                                                  text=f"Upgrade in progress: {int(remaining_time * INV_FPS)}",
                                                  color=(0, 255, 0, 255),
                                                  group=groups.g[layer + 1], batch=batch, anchor_y="bottom",
                                                  anchor_x="left",
                                                  font_size=0.013 * SCREEN_WIDTH),
                                )
        elif available == 3:
            self.sprites.append(pyglet.text.Label(x=SCREEN_WIDTH * 0.705, y=SCREEN_HEIGHT * 0.01, multiline=True,
                                                  width=SCREEN_WIDTH * .29,
                                                  text="Thou Posesseth This Development",
                                                  color=(0, 255, 0, 255),
                                                  group=groups.g[layer + 1], batch=batch, anchor_y="bottom",
                                                  anchor_x="left",
                                                  font_size=0.013 * SCREEN_WIDTH),
                                )
        else:
            self.sprites.append(pyglet.text.Label(x=SCREEN_WIDTH * 0.705, y=SCREEN_HEIGHT * 0.01, multiline=True,
                                                  width=SCREEN_WIDTH * .29,
                                                  text="locked",
                                                  color=(255, 0, 0, 255),
                                                  group=groups.g[layer + 1], batch=batch, anchor_y="bottom",
                                                  anchor_x="left",
                                                  font_size=0.013 * SCREEN_WIDTH),
                                )
        self.sprites.append(pyglet.text.Label(x=SCREEN_WIDTH * 0.85, y=SCREEN_HEIGHT * 0.91,
                                              text=upg.name,
                                              color=(250, 90, 30, 255),
                                              group=groups.g[layer + 1], batch=batch, anchor_y="bottom",
                                              anchor_x="center",
                                              font_size=0.025 * SCREEN_WIDTH))
        self.sprites.append(pyglet.text.Label(x=SCREEN_WIDTH * 0.85, y=SCREEN_HEIGHT * 0.89, multiline=True,
                                              width=SCREEN_WIDTH * .28,
                                              text=upgrade_stats[upg.name]["desc"],
                                              color=(200, 200, 200, 255),
                                              group=groups.g[layer + 1], batch=batch, anchor_y="top",
                                              anchor_x="center",
                                              font_size=0.019 * SCREEN_WIDTH))
        self.sprites.append(pyglet.text.Label(x=SCREEN_WIDTH * 0.85, y=SCREEN_HEIGHT * 0.8,
                                              text=upgrade_stats[upg.name]["flavor"],
                                              color=(200, 200, 200, 255),
                                              group=groups.g[layer + 1], batch=batch, anchor_y="top",
                                              anchor_x="center", multiline=True, width=SCREEN_WIDTH * .28,
                                              font_size=0.013 * SCREEN_WIDTH))
        self.open = True

    def close(self):
        self.open = False
        [e.delete() for e in self.sprites]
        super().delete()

    def update(self, dt):
        if self.remaining_time > 0:
            self.remaining_time -= dt * FPS
            if self.remaining_time > 0:
                self.sprites[0].text = f"Upgrade in progress: {int(self.remaining_time * INV_FPS)}"
            else:
                self.sprites[0].text = "Thou Posesseth This Development"


class Upgrade_default(Upgrade):
    previous = []
    name = "The Beginning"


class Upgrade_test_1(Upgrade):
    image = images.Bear
    previous = []
    name = "Bigger Stalls"

    def on_finish(self):
        self.player.unlock_unit(Bear)


class Upgrade_catapult(Upgrade):
    name = "Catapults"
    previous = []
    image = images.Trebuchet

    def on_finish(self):
        self.player.unlock_unit(Trebuchet)


class Upgrade_bigger_arrows(Upgrade):
    name = "Bigger Arrows"
    previous = []
    image = images.Arrow_upg

    def on_finish(self):
        aura(
            effect_combined, (
                (effect_stat_mult, effect_stat_mult),
                (
                    ("dmg", float(upgrade_stats[self.name]["mod"])),
                    ("bullet_scale", 2)
                )
            ), self.player.game, self.player.side, targets=["arrows"]
        )


class Upgrade_more_chestplates(Upgrade):
    name = "More Chestplates"
    previous = []
    image = images.Chestplates

    def on_finish(self):
        aura(effect_stat_mult, ("health", float(upgrade_stats[self.name]["mod"])),
             self.player.game, self.player.side,
             targets=["footman"],
             )


class Upgrade_bigger_rocks(Upgrade):
    name = "Bigger Rocks"
    previous = []
    image = images.Boulder

    def on_finish(self):
        aura(effect_combined, (
            (effect_stat_mult, effect_stat_mult, effect_stat_mult),
            (
                ("dmg", float(upgrade_stats[self.name]["mod_dmg"])),
                ("explosion_radius", float(upgrade_stats[self.name]["mod_rad"])),
                ("bullet_scale", 2)
            )
        ),
             self.player.game, self.player.side, targets=["boulders"]
             )


class Upgrade_egg(Upgrade):
    name = "Egg Cannon"
    previous = []
    image = images.Egg

    def on_finish(self):
        self.player.unlock_unit(Tower211)


class Upgrade_mines(Upgrade):
    name = "Mines"
    previous = []
    image = images.Mine

    def on_finish(self):
        self.player.unlock_unit(Tower22)


class Upgrade_faster_archery(Upgrade):
    name = "Faster Archery"
    previous = []
    image = images.Arrow_upg_2

    def on_finish(self):
        aura(effect_stat_mult, ("cd", float(upgrade_stats[self.name]["mod"])),
             self.player.game, self.player.side,
             targets=["arrows"])


class Upgrade_vigorous_farming(Upgrade):
    name = "Vigorous Farming"
    previous = []
    image = images.Farm1

    def on_finish(self):
        aura(effect_stat_mult, ("production", float(upgrade_stats[self.name]["mod"])),
             self.player.game, self.player.side,
             targets=["farm"])


class Upgrade_nanobots(Upgrade):
    name = "Nanobots"
    previous = []
    image = images.Farm1

    def on_finish(self):
        aura(effect_regen, (float(upgrade_stats[self.name]["mod"]),),
             self.player.game, self.player.side,
             targets=["building", "wall"], require_1_tag=True)


class Upgrade_walls(Upgrade):
    name = "Tough Walls"
    previous = []
    image = images.Farm1

    def on_finish(self):
        aura(effect_stat_mult, ("resistance", float(upgrade_stats[self.name]["mod"])),
             self.player.game, self.player.side,
             targets=["wall"])


class Upgrade_necromancy(Upgrade):
    name = "Necromancy"
    previous = []
    image = images.Beam

    def on_finish(self):
        self.player.unlock_unit(Necromancer)


class Upgrade_superior_pyrotechnics(Upgrade):
    name = "Superior Pyrotechnics"
    previous = []
    image = images.Beam

    def on_finish(self):
        self.player.unlock_unit(Tower231)


class Upgrade_golem(Upgrade):
    image = images.Boulder
    previous = []
    name = "Golem"

    def on_finish(self):
        self.player.unlock_unit(Golem)


class Upgrade_trees(Upgrade):
    image = images.Tree
    previous = []
    name = "Trees"

    def on_finish(self):
        self.player.unlock_unit(Tree_spell)


class Upgrade_nature(Upgrade):
    image = images.Boulder
    excludes = []
    previous = []
    name = "Nature"

    def on_finish(self):
        self.player.unlock_unit(TownHall13)


class Upgrade_fire(Upgrade):
    image = images.Boulder
    excludes = []
    previous = []
    name = "Fire"

    def on_finish(self):
        self.player.unlock_unit(TownHall12)


class Upgrade_frost(Upgrade):
    image = images.Boulder
    excludes = []
    previous = []
    name = "Frost"

    def on_finish(self):
        self.player.unlock_unit(TownHall11)


class Upgrade_tech(Upgrade):
    image = images.Boulder
    excludes = []
    previous = []
    name = "Tech"

    def on_finish(self):
        self.player.unlock_unit(TownHall14)


for uuuu in [Upgrade_frost, Upgrade_fire, Upgrade_nature, Upgrade_tech]:
    uuuu.excludes = [Upgrade_frost, Upgrade_fire, Upgrade_nature, Upgrade_tech]
    uuuu.excludes.remove(uuuu)

possible_upgrades = [Upgrade_default, Upgrade_test_1, Upgrade_bigger_arrows, Upgrade_catapult, Upgrade_bigger_rocks,
                     Upgrade_egg, Upgrade_faster_archery, Upgrade_vigorous_farming, Upgrade_mines, Upgrade_necromancy,
                     Upgrade_nanobots, Upgrade_walls, Upgrade_superior_pyrotechnics, Upgrade_golem, Upgrade_frost,
                     Upgrade_fire, Upgrade_nature, Upgrade_tech, Upgrade_trees, Upgrade_more_chestplates]

for uuuu in possible_upgrades:
    uuuu.x, uuuu.y = int(upgrade_stats[uuuu.name]["x"]), int(upgrade_stats[uuuu.name]["y"])
    fromme = upgrade_stats[uuuu.name]["from"].split("&")
    for uuu2 in possible_upgrades:
        if uuu2.name in fromme:
            uuuu.previous.append(uuu2)


class Spell:
    name = "Spell"
    entity_type = "spell"

    def __init__(self, game, side, tick, x, y):
        game.players[side].spells.append(self)
        self.spawning = game.ticks - tick
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

    def graphics_update(self, dt):
        pass

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

    def __init__(self, game, side, tick, x, y):
        super().__init__(game, side, tick, x, y)
        self.x1, self.y1 = game.players[side].TownHall.x, game.players[side].TownHall.y
        self.dx, self.dy = self.x - self.x1, self.y - self.y1
        self.radius = unit_stats[self.name]["radius"]
        self.sprite = client_utility.animation(self.x1, self.y1, self.radius * 0.6, game, img=images.Fireball,
                                               loop=True, duration=3)
        self.sprite.rotation = 90 - get_rotation(self.dx, self.dy) * 180 / math.pi
        self.dmg = unit_stats[self.name]["dmg"]
        self.delay *= distance(self.x1, self.y1, x, y)
        self.delay = max(self.delay, ACTION_DELAY * FPS)

    def graphics_update(self, dt):
        progress = self.spawning / self.delay
        self.sprite.true_x = self.x1 + self.dx * progress
        self.sprite.true_y = self.y1 + self.dy * progress
        self.sprite.tick(dt)

    def main(self):
        self.sprite.delete()
        AOE_damage(self.x, self.y, self.radius, self.dmg, self, self.game, "spell")
        animation_explosion(self.x, self.y, self.radius * 2, 100, self.game)


class Freeze(Spell):
    name = "Freeze"

    def __init__(self, game, side, tick, x, y):
        super().__init__(game, side, tick, x, y)
        self.radius = unit_stats[self.name]["radius"]
        self.duration = unit_stats[self.name]["duration"]

    def main(self):
        AOE_aura(effect_freeze, (self.duration,), [self.x, self.y, self.radius], self.game, 1 - self.side, 0)
        animation_freeze(self.x, self.y, self.radius * 2, self.duration * INV_FPS, self.game)


class Tree_spell(Spell):
    name = "Tree_spell"

    def __init__(self, game, side, tick, x, y):
        super().__init__(game, side, tick, x, y)
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

    def __init__(self, game, side, tick, x, y):
        super().__init__(game, side, tick, x, y)
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
        animation_rage(self.x, self.y, self.radius * 2, self.duration * INV_FPS, self.game)


possible_spells = [Fireball, Freeze, Rage, Tree_spell]
