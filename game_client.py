from typing import List, Any

from imports import *
import groups
from constants import *
import images
import client_utility


class Game:
    def __init__(self, side, batch, connection, time0):
        self.side, self.batch = side, batch
        self.chunks = {}
        self.players = [player(0, self), player(1, self)]
        self.connection = connection
        self.batch = batch
        self.cam_move_speed = 3
        self.start_time = time0
        self.ticks = 0
        self.camx, self.camy = 0, 0
        self.camx_moving, self.camy_moving = 0, 0
        self.background_texgroup = client_utility.TextureBindGroup(images.Background, layer=0)
        self.background = batch.add(
            4, pyglet.gl.GL_QUADS, self.background_texgroup,
            ("v2i", (0, 0, SCREEN_WIDTH, 0,
                     SCREEN_WIDTH, SCREEN_HEIGHT, 0, SCREEN_HEIGHT)),
            ("t2f", (0, 0, SCREEN_WIDTH / 512, 0, SCREEN_WIDTH / 512, SCREEN_HEIGHT / 512,
                     0, SCREEN_HEIGHT / 512))
        )
        self.UI_bottomBar = UI_bottom_bar(self)
        self.UI_categories = UI_categories(self, self.UI_bottomBar)
        self.unit_formation_rows = UNIT_FORMATION_ROWS
        self.unit_formation_columns = UNIT_FORMATION_COLUMNS
        self.unit_formation = UI_formation(self)
        self.UI_toolbars = [self.UI_bottomBar, self.UI_categories, self.unit_formation]
        self.selected = selection_none(self)
        self.money = pyglet.text.Label(x=SCREEN_WIDTH * 0.995, y=SCREEN_HEIGHT * 0.995, text="Gold:0",
                                       color=(255, 240, 0, 255),
                                       group=groups.g[9], batch=self.batch, anchor_y="top", anchor_x="right",
                                       font_size=20 * SPRITE_SIZE_MULT)

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

    def clear_chunks(self):
        for e in self.chunks:
            self.chunks[e].clear_units()

    def get_chunk(self, c):
        if c in self.chunks:
            return c
        return None

    def select(self, sel):
        self.selected.end()
        self.selected = sel(self)

    def tick(self):
        while self.ticks < FPS * (time.time() - self.start_time):
            self.clear_chunks()
            self.players[0].tick_units()
            self.players[1].tick_units()
            self.players[0].tick()
            self.players[1].tick()
            self.ticks += 1
            self.players[0].gain_money(PASSIVE_INCOME)
            self.players[1].gain_money(PASSIVE_INCOME)
        self.update_cam()
        self.players[0].graphics_update()
        self.players[1].graphics_update()
        self.selected.tick()
        self.batch.draw()

    def network(self, data):
        if "action" in data:
            if data["action"] == "place_tower":
                Tower(data["ID"], data["xy"][0], data["xy"][1], data["tick"], data["side"], self)
                return
            if data["action"] == "place_wall":
                t1, t2 = self.find_tower(data["ID1"], data["side"]), self.find_tower(data["ID2"], data["side"])
                Wall(data["ID"], t1, t2, data["tick"], data["side"], self)
                return
            if data["action"] == "summon_formation":
                Formation(data["ID"], data["instructions"], data["troops"], data["tick"], data["side"], self)
                return

    def mouse_move(self, x, y, dx, dy):
        [e.mouse_move(x, y) for e in self.UI_toolbars]
        self.selected.mouse_move(x, y)

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
        self.selected.key_press(symbol, modifiers)

    def key_release(self, symbol, modifiers):
        if symbol == key.D:
            self.camx_moving = max(self.camx_moving - self.cam_move_speed, -self.cam_move_speed)
        elif symbol == key.W:
            self.camy_moving = max(self.camy_moving - self.cam_move_speed, -self.cam_move_speed)
        elif symbol == key.A:
            self.camx_moving = min(self.camx_moving + self.cam_move_speed, self.cam_move_speed)
        elif symbol == key.S:
            self.camy_moving = min(self.camy_moving + self.cam_move_speed, self.cam_move_speed)

    def mouse_press(self, x, y, button, modifiers):
        if True in [e.mouse_click(x, y) for e in self.UI_toolbars]:
            return
        self.selected.mouse_click(x, y)

    def mouse_release(self, x, y, button, modifiers):
        [e.mouse_release(x, y) for e in self.UI_toolbars]
        self.selected.mouse_release(x, y)

    def mouse_scroll(self, x, y, scroll_x, scroll_y):
        pass

    def update_cam(self):
        self.camx += self.camx_moving
        self.camy += self.camy_moving
        x, y = self.camx / 512, self.camy / 512
        self.background.tex_coords = (x, y, x + SCREEN_WIDTH / 512, y, x + SCREEN_WIDTH / 512,
                                      y + SCREEN_HEIGHT / 512, x, y + SCREEN_HEIGHT / 512)
        [e.update_cam(self.camx, self.camy) for e in self.players]
        self.selected.update_cam(self.camx, self.camy)

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

    def find_formation(self, ID, side):
        for e in self.players[side].formations:
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
        if self.side == self.game.side:
            self.game.money.text = "Gold: " + str(int(self.money))

    def attempt_purchase(self, amount):
        if self.money < amount:
            return False
        self.money -= amount
        if self.side == self.game.side:
            self.game.money.text = "Gold: " + str(int(self.money))
        return True

    def tick_units(self):
        # ticks before other stuff to ensure the units are in their chunks
        [e.tick() for e in self.units]

    def tick(self):
        [e.tick() for e in self.towers]
        [e.tick() for e in self.walls]
        [e.tick() for e in self.formations]
        self.TownHall.tick()

    def graphics_update(self):
        [e.graphics_update() for e in self.units]
        [e.graphics_update() for e in self.towers]
        [e.graphics_update() for e in self.walls]
        self.TownHall.graphics_update()

    def update_cam(self, x, y):
        [e.update_cam(x, y) for e in self.units]
        [e.update_cam(x, y) for e in self.all_buildings]
        [e.update_cam(x, y) for e in self.formations]


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


class UI_bottom_bar(client_utility.toolbar):
    def __init__(self, game):
        super().__init__(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT / 5, game.batch)
        self.game = game
        self.page = 0
        self.load_page(0)

    def load_page(self, n):
        self.unload_page()
        i = 0
        for e in selects_all[n]:
            self.add(self.game.select, SCREEN_WIDTH * (0.01 + 0.1 * i), SCREEN_WIDTH * 0.01,
                     SCREEN_WIDTH * 0.09, SCREEN_WIDTH * 0.09, e.img, args=(e,))
            i += 1

    def unload_page(self):
        [e.delete() for e in self.buttons]
        self.buttons = []


class UI_formation(client_utility.toolbar):
    units: list[list[int]]

    def __init__(self, game):
        self.rows, self.columns = game.unit_formation_rows, game.unit_formation_columns
        self.dot_size = SCREEN_HEIGHT * 0.1788 / self.rows
        self.game = game
        self.dot_scale = self.dot_size / images.UnitSlot.width

        super().__init__(SCREEN_WIDTH - self.dot_size * (self.columns + 4), 0, self.dot_size * (self.columns + 4),
                         self.dot_size * (self.rows + 4) + SCREEN_HEIGHT * 0.1, game.batch,
                         image=images.UnitFormFrame, layer=7)

        self.units = [[-1 for _ in range(self.rows)] for _ in range(self.columns)]

        self.sprites = [[client_utility.sprite_with_scale(images.UnitSlot, self.dot_scale, 1, 1,
                                                          self.x + self.dot_size * (j + 2.5),
                                                          self.y + self.dot_size * (i + 2.5),
                                                          batch=game.batch, group=groups.g[8])
                         for i in range(self.rows)] for j in range(self.columns)]
        self.add(self.send, self.x, self.height - SCREEN_HEIGHT * 0.1, self.width, SCREEN_HEIGHT * 0.1,
                 image=images.Cancelbutton)
        self.cost_count = pyglet.text.Label(x=self.x + self.width / 2, y=5, text="Cost: 0", color=(255, 240, 0, 255),
                                            group=groups.g[9], batch=self.batch, anchor_x="center", anchor_y="bottom",
                                            font_size=20 * SPRITE_SIZE_MULT)
        self.cost = 0

    def sucessful_click(self, x, y):
        if self.x + self.dot_size * 2 < x < self.x + self.dot_size * (2 + self.columns) and \
                self.y + self.dot_size * 2 < y < self.y + self.dot_size * (2 + self.rows):
            self.game.selected.clicked_unit_slot(int((x - (self.x + self.dot_size * 2)) // self.dot_size),
                                                 int((y - (self.y + self.dot_size * 2)) // self.dot_size))

    def mouse_click(self, x, y):
        if super().mouse_click(x, y):
            self.sucessful_click(x, y)

    def mouse_drag(self, x, y):
        if super().mouse_drag:
            self.sucessful_click(x, y)

    def send(self):
        self.game.select(selection_unit_formation)

    def set_unit(self, x, y, num: int):
        if self.units[x][y] == num:
            return
        if self.units[x][y] == -1:
            self.cost += possible_units[num].get_cost([])
        elif num == -1:
            self.cost -= possible_units[self.units[x][y]].get_cost([])
        else:
            self.cost += possible_units[num].get_cost([]) - possible_units[self.units[x][y]].get_cost([])
        self.cost_count.text = "Cost: " + str(int(self.cost))
        self.units[x][y] = num
        if num != -1:
            self.sprites[x][y].delete()
            a = possible_units[num].image
            self.sprites[x][y] = client_utility.sprite_with_scale(a, self.dot_size / a.width, 1, 1,
                                                                  self.x + self.dot_size * (x + 2.5),
                                                                  self.y + self.dot_size * (y + 2.5),
                                                                  batch=self.game.batch, group=groups.g[8])
        else:
            self.sprites[x][y].delete()
            self.sprites[x][y] = client_utility.sprite_with_scale(images.UnitSlot, self.dot_scale, 1, 1,
                                                                  self.x + self.dot_size * (x + 2.5),
                                                                  self.y + self.dot_size * (y + 2.5),
                                                                  batch=self.game.batch, group=groups.g[8])


class UI_categories(client_utility.toolbar):
    def __init__(self, game, bb):
        super().__init__(0, bb.height, SCREEN_WIDTH, SCREEN_HEIGHT * 0.05, game.batch)
        i = 0
        for _ in selects_all:
            self.add(bb.load_page, SCREEN_WIDTH * (0.01 + 0.1 * i), bb.height + SCREEN_HEIGHT * 0.005,
                     SCREEN_WIDTH * 0.09, SCREEN_HEIGHT * 0.04, args=(i,))
            i += 1


# #################   ---/core---  #################
# #################  ---selects---  #################

class selection:
    def __init__(self, game):
        self.cancelbutton = client_utility.button(self.end, SCREEN_WIDTH * 0.01, SCREEN_HEIGHT * 0.9,
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
        self.game.unit_formation.set_unit(x, y, -1)


class selection_none(selection):
    def __init__(self, game):
        self.game = game

    def end(self):
        pass


class selection_tower(selection):
    img = images.Towerbutton

    def __init__(self, game):
        super().__init__(game)
        self.camx, self.camy = 0, 0
        self.size = unit_stats["Tower"]["size"]
        self.sprite = pyglet.sprite.Sprite(images.Intro, x=0,
                                           y=0, batch=game.batch,
                                           group=groups.g[2])
        self.sprite.scale = self.size / self.sprite.width
        self.sprite.opacity = 100
        self.update_cam(self.game.camx, self.game.camy)

    def mouse_move(self, x, y):
        self.sprite.update(x=x - self.size / 2, y=y - self.size / 2)
        self.cancelbutton.mouse_move(x, y)

    def mouse_click(self, x, y):
        if not self.cancelbutton.mouse_click(x, y):
            self.game.connection.Send({"action": "place_tower", "xy": [(x + self.camx) / SPRITE_SIZE_MULT,
                                                                       (y + self.camy) / SPRITE_SIZE_MULT]})
            self.end()

    def mouse_release(self, x, y):
        self.cancelbutton.mouse_release(x, y)

    def end(self):
        self.sprite.delete()
        super().end()

    def update_cam(self, x, y):
        self.camx, self.camy = x, y


class selection_wall(selection):
    img = images.Towerbutton

    def __init__(self, game):
        super().__init__(game)
        self.selected1, self.selected2 = None, None
        self.buttons = []
        self.camx, self.camy = game.camx, game.camy
        for e in game.players[game.side].towers:
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


class selection_unit_formation(selection):
    img = images.gunmanR

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
        self.actual_indicator_points = [0 for i in range(8)]
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

    def clicked_unit_slot(self, x, y):
        self.game.unit_formation.set_unit(x, y, 0)

    def key_press(self, button, modifiers):
        if button == key.ENTER:
            self.game.connection.Send(
                {"action": "summon_formation", "instructions": self.instructions, "troops": self.troops})
            self.end()


class selection_unit(selection):
    img = images.gunmanR
    num = 0

    def clicked_unit_slot(self, x, y):
        self.game.unit_formation.set_unit(x, y, self.num)

    def mouse_click(self, x, y):
        if not self.cancelbutton.mouse_click(x, y):
            pass

    def mouse_release(self, x, y):
        self.cancelbutton.mouse_release(x, y)


# ################# ---/selects--- #################
# #################   ---units---  #################

class TownHall:
    name = "TownHall"

    def __init__(self, x, y, side, game):
        self.entity_type = "townhall"
        self.x, self.y = x, y
        self.side = side
        self.size = unit_stats[self.name]["size"]
        self.hp = self.maxhp = unit_stats[self.name]["hp"]
        self.sprite = pyglet.sprite.Sprite(images.Tower, x=x * SPRITE_SIZE_MULT,
                                           y=y * SPRITE_SIZE_MULT, batch=game.batch,
                                           group=groups.g[2])
        self.sprite.scale = self.size * SPRITE_SIZE_MULT / self.sprite.width
        self.game = game
        self.chunks = get_chunks(x, y, self.size)
        self.exists = True
        for e in self.chunks:
            game.add_townhall_to_chunk(self, e)
        hpbar_y_centre = self.sprite.y
        hpbar_y_range = 2 * SPRITE_SIZE_MULT
        hpbar_x_centre = self.sprite.x
        hpbar_x_range = self.size * SPRITE_SIZE_MULT / 2
        self.hpbar = game.batch.add(
            8, pyglet.gl.GL_QUADS, groups.g[6],
            ("v2f", (hpbar_x_centre - hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre - hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range)),
            ("c3B", (0, 255, 0, 0, 255, 0, 0, 255, 0, 0, 255, 0, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50)
            if self.game.side == self.side else (
                163, 73, 163, 163, 73, 163, 163, 73, 163, 163, 73, 163, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50))
        )

    def update_hpbar(self):
        if not self.exists:
            return
        hpbar_y_centre = self.sprite.y
        hpbar_y_range = 2 * SPRITE_SIZE_MULT
        hpbar_x_centre = self.sprite.x
        hpbar_x_range = self.size * SPRITE_SIZE_MULT / 2
        health_size = hpbar_x_range * (2 * self.hp / self.maxhp - 1)
        self.hpbar.vertices = (hpbar_x_centre - hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                               hpbar_x_centre - hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre - hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre - hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range)

    def take_damage(self, amount, source):
        self.hp -= amount
        if self.hp <= 0:
            self.die()

    def die(self):
        self.sprite.delete()
        print("game over")

    def distance_to_point(self, x, y):
        return distance(self.x, self.y, x, y) - self.size / 2

    def update_cam(self, x, y):
        self.sprite.update(x=self.x * SPRITE_SIZE_MULT - x,
                           y=self.y * SPRITE_SIZE_MULT - y)

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

    def graphics_update(self):
        self.update_hpbar()


class Tower:
    name = "Tower"

    def __init__(self, ID, x, y, tick, side, game):
        assert (game.players[side].attempt_purchase(self.get_cost([])))
        self.entity_type = "tower"
        self.x, self.y = x, y
        self.exists = False
        self.spawning = game.ticks - tick
        self.ID = ID
        self.side = side
        self.size = unit_stats[self.name]["size"]
        self.chunks = get_chunks(x, y, self.size)
        for e in self.chunks:
            game.add_tower_to_chunk(self, e)
        self.hp = self.maxhp = unit_stats[self.name]["hp"]
        self.sprite = pyglet.sprite.Sprite(images.Tower, x=x * SPRITE_SIZE_MULT,
                                           y=y * SPRITE_SIZE_MULT, batch=game.batch,
                                           group=groups.g[3])
        self.sprite2 = pyglet.sprite.Sprite(images.TowerCrack, x=x * SPRITE_SIZE_MULT,
                                            y=y * SPRITE_SIZE_MULT, batch=game.batch,
                                            group=groups.g[4])
        self.sprite2.opacity = 0
        self.sprite2.scale = self.size * SPRITE_SIZE_MULT / self.sprite2.width
        self.sprite.scale = self.size * SPRITE_SIZE_MULT / self.sprite.width
        self.sprite.opacity = 70
        game.players[side].towers.append(self)
        game.players[side].all_buildings.append(self)
        self.game = game
        self.update_cam(self.game.camx, self.game.camy)
        hpbar_y_centre = self.sprite.y
        hpbar_y_range = 2 * SPRITE_SIZE_MULT
        hpbar_x_centre = self.sprite.x
        hpbar_x_range = self.size * SPRITE_SIZE_MULT / 2
        self.hpbar = game.batch.add(
            8, pyglet.gl.GL_QUADS, groups.g[6],
            ("v2f", (hpbar_x_centre - hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre - hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range)),
            ("c3B", (0, 255, 0, 0, 255, 0, 0, 255, 0, 0, 255, 0, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50)
            if self.game.side == self.side else (
                163, 73, 163, 163, 73, 163, 163, 73, 163, 163, 73, 163, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50))
        )

    def update_hpbar(self):
        if not self.exists:
            return
        hpbar_y_centre = self.sprite.y
        hpbar_y_range = 2 * SPRITE_SIZE_MULT
        hpbar_x_centre = self.sprite.x
        hpbar_x_range = self.size * SPRITE_SIZE_MULT / 2
        health_size = hpbar_x_range * (2 * self.hp / self.maxhp - 1)
        self.hpbar.vertices = (hpbar_x_centre - hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                               hpbar_x_centre - hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre - hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre - hpbar_y_range,
                               hpbar_x_centre + health_size, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                               hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range)

    def distance_to_point(self, x, y):
        return distance(self.x, self.y, x, y) - self.size / 2

    @classmethod
    def get_cost(cls, params):
        return unit_stats[cls.name]["cost"]

    def die(self):
        self.game.players[self.side].towers.remove(self)
        self.game.players[self.side].all_buildings.remove(self)
        self.sprite.delete()
        self.sprite2.delete()
        self.hpbar.delete()
        self.exists = False

    def take_damage(self, amount, source):
        if not self.exists:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.die()
            return
        self.sprite2.opacity = 255 * (self.maxhp - self.hp) / self.maxhp

    def update_cam(self, x, y):
        self.sprite.update(x=self.x * SPRITE_SIZE_MULT - x, y=self.y * SPRITE_SIZE_MULT - y)
        self.sprite2.update(x=self.x * SPRITE_SIZE_MULT - x, y=self.y * SPRITE_SIZE_MULT - y)

    def tick(self):
        if self.spawning < FPS:
            self.spawning += 1
        if self.spawning == FPS:
            self.exists = True
            self.sprite.opacity = 255
            self.tick = self.tick2

    def tick2(self):
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

    def graphics_update(self):
        self.update_hpbar()


class Wall:
    name = "Wall"

    def __init__(self, ID, t1, t2, tick, side, game):
        assert (game.players[side].attempt_purchase(self.get_cost([])))
        self.entity_type = "wall"
        self.exists = False
        self.spawning = game.ticks - tick
        self.ID = ID
        self.x1, self.y1, self.x2, self.y2 = t1.x, t1.y, t2.x, t2.y
        self.length = ((self.x1 - self.x2) ** 2 + (self.y1 - self.y2) ** 2) ** .5
        self.norm_vector = ((self.y2 - self.y1) / self.length, (self.x1 - self.x2) / self.length)
        self.line_c = -self.norm_vector[0] * self.x1 - self.norm_vector[1] * self.y1
        self.crossline_c = (-self.norm_vector[1] * (self.x1 + self.x2) + self.norm_vector[0] * (self.y1 + self.y2)) * .5
        self.side = side
        self.tower_1, self.tower_2 = t1, t2
        self.width = unit_stats[self.name]["width"]
        self.hp = self.maxhp = unit_stats[self.name]["hp"]
        self.game = game
        game.players[side].walls.append(self)
        game.players[side].all_buildings.append(self)
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

    @classmethod
    def get_cost(cls, params):
        return unit_stats[cls.name]["cost"]

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

    def die(self):
        self.sprite.delete()
        self.crack_sprite.delete()
        self.game.players[self.side].walls.remove(self)
        self.game.players[self.side].all_buildings.remove(self)
        self.exists = False

    def take_damage(self, amount, source):
        if not self.exists:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.die()
            return
        self.crack_sprite.colors[3::4] = [int((255 * (self.maxhp - self.hp)) // self.maxhp)] * 4

    def shove(self):
        for e in self.game.players[1 - self.side].units:
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
        if self.spawning < FPS:
            self.spawning += 1
        if self.spawning == FPS:
            self.exists = True
            self.sprite.colors = (255,) * 16
            self.tick = self.tick2

    def tick2(self):
        self.shove()

    def graphics_update(self):
        pass


class Formation:
    def __init__(self, ID, instructions, troops, tick, side, game):
        assert (game.players[side].attempt_purchase(self.get_cost([troops])))
        self.entity_type = "formation"
        self.exists = False
        self.spawning = game.ticks - tick
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

    def update_cam(self, x, y):
        [e.update_cam(x, y) for e in self.troops]

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
    image = images.Cancelbutton
    name = "None"

    def __init__(self, ID, x, y, side, column, row, game: Game, formation: Formation):
        self.entity_type = "unit"
        self.last_camx, self.last_camy = game.camx, game.camy
        self.ID = ID
        self.lifetime = 0
        self.side = side
        self.game = game
        self.formation = formation
        self.x, self.y = x, y
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
            8, pyglet.gl.GL_QUADS, groups.g[6],
            ("v2f", (hpbar_x_centre - hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre - hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre - hpbar_y_range,
                     hpbar_x_centre + hpbar_x_range, hpbar_y_centre + hpbar_y_range)),
            ("c3B", (0, 255, 0, 0, 255, 0, 0, 255, 0, 0, 255, 0, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50)
            if self.game.side == self.side else (
                163, 73, 163, 163, 73, 163, 163, 73, 163, 163, 73, 163, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50))
        )

        self.speed = unit_stats[self.name]["speed"] / FPS
        self.health = self.max_health = unit_stats[self.name]["hp"]
        self.damage = unit_stats[self.name]["dmg"]
        self.attack_cooldown = unit_stats[self.name]["cd"]
        self.current_cooldown = 0
        self.reach = unit_stats[self.name]["reach"]
        self.sprite.opacity = 70
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

    def take_damage(self, amount, source):
        if not self.exists:
            return
        self.health -= amount
        if self.health <= 0:
            self.die()

    @classmethod
    def get_cost(cls, params):
        return unit_stats[cls.name]["cost"]

    def update_hpbar(self):
        if not self.exists:
            return
        hpbar_y_centre = self.sprite.y
        hpbar_y_range = 2 * SPRITE_SIZE_MULT
        hpbar_x_centre = self.sprite.x
        hpbar_x_range = self.size * SPRITE_SIZE_MULT / 2
        health_size = hpbar_x_range * (2 * self.health / self.max_health - 1)
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

    def die(self):
        self.formation.troops.remove(self)
        self.game.players[self.side].units.remove(self)
        self.game = None
        self.sprite.delete()
        self.hpbar.delete()
        if not self.formation.troops:
            self.formation.delete()
        self.formation = None
        self.exists = False

    def take_knockback(self, x, y, source):
        if not self.exists:
            return
        self.x += x
        self.y += y
        if source.side != self.side:
            if source.entity_type == "unit" and source not in self.formation.all_targets:
                self.formation.attack(source.formation)
            elif source.entity_type in ["tower", "townhall", "wall"] and source not in self.formation.all_targets:
                self.formation.attack(source)

    def rotate(self, x, y):
        if x == y == 0:
            return
        inv_hypot = inv_h(x, y)
        r = get_rotation(x, y)
        self.rotation = r
        self.vx, self.vy = x * inv_hypot * self.speed, y * inv_hypot * self.speed

    def summon_done(self):
        self.exists = True
        self.sprite.opacity = 255
        self.tick = self.tick2

    def update_cam(self, x, y):
        self.sprite.update(x=self.x * SPRITE_SIZE_MULT - x, y=self.y * SPRITE_SIZE_MULT - y)

    def try_move(self, x, y):
        if self.x == x and self.y == y:
            return
        self.desired_x, self.desired_y = x, y
        self.rotate(x - self.x, y - self.y)
        self.reached_goal = False

    def shove(self):
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

    def graphics_update(self):
        if self.exists:
            self.sprite.update(x=self.x * SPRITE_SIZE_MULT - self.game.camx,
                               y=self.y * SPRITE_SIZE_MULT - self.game.camy,
                               rotation=-self.rotation * 180 / math.pi + 90)
            self.update_hpbar()

    @classmethod
    def get_image(cls):
        return [cls.image, unit_stats[cls.name]["vwidth"] * SPRITE_SIZE_MULT / cls.image.width, 1, 1]


class Swordsman(Unit):
    image = images.Swordsman
    name = "Swordsman"

    def __init__(self, ID, x, y, side, column, row, game, formation):
        super().__init__(ID, x, y, side, column, row, game, formation)

    def attack(self, target):
        target.take_damage(self.damage, self)


class selection_swordsman(selection_unit):
    img = images.gunmanR
    num = 0


class Archer(Unit):
    image = images.Bowman
    name = "Archer"

    def __init__(self, ID, x, y, side, column, row, game, formation):
        super().__init__(ID, x, y, side, column, row, game, formation)

    def attack(self, target):
        target.take_damage(self.damage, self)


class selection_archer(selection_unit):
    img = images.gunmanG
    num = 1


possible_units = [Swordsman, Archer]
selects_p1 = [selection_tower, selection_wall]
selects_p2 = [selection_swordsman, selection_archer]
selects_all = [selects_p1, selects_p2]

# #################  ---/units---  #################
