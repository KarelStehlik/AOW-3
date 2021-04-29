from imports import *
import groups
from constants import *
import images
import client_utility


class Game:
    def __init__(self, side, batch, connection, time0):
        self.side, self.batch = side, batch
        self.players = [player(0, self), player(1, self)]
        self.connection = connection
        self.batch = batch
        self.cam_move_speed = 3
        self.start_time = time0
        self.ticks = 0
        print(time.time(), self.start_time)
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

    def select(self, sel):
        self.selected.end()
        self.selected = sel(self)

    def tick(self):
        while self.ticks < FPS * (time.time() - self.start_time):
            #print(f"\n\ntick {self.ticks}:\nplayer 0:")
            #a = time.time()
            self.players[0].tick()
            #print((time.time() - a) * 1000, "ms total")
            #print("player 1:")
            #a = time.time()
            self.players[1].tick()
            #print((time.time() - a) * 1000, "ms total")
            self.ticks += 1
        self.update_cam()
        #a=time.time()
        self.players[0].graphics_update()
        self.players[1].graphics_update()
        #print((time.time() - a) * 1000, "ms graphics update")
        self.selected.tick()
        #a = time.time()
        self.batch.draw()
        #print((time.time() - a) * 1000, "ms draw")

    def network(self, data):
        if "action" in data:
            if data["action"] == "place_tower":
                Tower(data["ID"], data["xy"][0], data["xy"][1], data["tick"], data["side"], self)
                return
            if data["action"] == "place_wall":
                Wall(data["ID"], self.find_tower(data["ID1"], data["side"]),
                     self.find_tower(data["ID2"], data["side"]), data["tick"], data["side"], self)
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

    def tick(self):
        #a = time.time()
        [e.tick() for e in self.units]
        #print((time.time() - a) * 1000, "ms units tick")
        #a = time.time()
        [e.tick() for e in self.towers]
        #print((time.time() - a) * 1000, "ms towers tick")
        #a = time.time()
        [e.tick() for e in self.walls]
        #print((time.time() - a) * 1000, "ms walls tick")
        #a = time.time()
        [e.tick() for e in self.formations]
        #print((time.time() - a) * 1000, "ms formations tick")
        #a = time.time()
        self.TownHall.tick()
        #print((time.time()-a)*1000, "ms th tick")

    def graphics_update(self):
        [e.graphics_update() for e in self.units]
        [e.graphics_update() for e in self.towers]
        [e.graphics_update() for e in self.walls]
        self.TownHall.graphics_update()

    def update_cam(self, x, y):
        [e.update_cam(x, y) for e in self.units]
        [e.update_cam(x, y) for e in self.all_buildings]
        [e.update_cam(x, y) for e in self.formations]


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
    def __init__(self, game):
        self.rows, self.columns = game.unit_formation_rows, game.unit_formation_columns
        self.dot_size = SCREEN_HEIGHT * 0.1788 / self.rows
        self.game = game
        self.dot_scale = self.dot_size / images.UnitSlot.width

        super().__init__(SCREEN_WIDTH - self.dot_size * (self.columns + 4), 0, self.dot_size * (self.columns + 4),
                         self.dot_size * (self.rows + 4) + SCREEN_HEIGHT * 0.1, game.batch,
                         image=images.UnitFormFrame, layer=5)

        self.units = [[None for _ in range(self.rows)] for _ in range(self.columns)]

        self.sprites = [[client_utility.sprite_with_scale(images.UnitSlot, self.dot_scale, 1, 1,
                                                          self.x + self.dot_size * (j + 2.5),
                                                          self.y + self.dot_size * (i + 2.5),
                                                          batch=game.batch, group=groups.g[6])
                         for i in range(self.rows)] for j in range(self.columns)]
        self.add(self.send, self.x, self.height - SCREEN_HEIGHT * 0.1, self.width, SCREEN_HEIGHT * 0.1,
                 image=images.Cancelbutton)

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

    def set_unit(self, x, y, num):
        if self.units[x][y] == num:
            return
        self.units[x][y] = num
        if num is not None:
            self.sprites[x][y].delete()
            a = possible_units[num].image
            self.sprites[x][y] = client_utility.sprite_with_scale(a, self.dot_size / a.width, 1, 1,
                                                                  self.x + self.dot_size * (x + 2.5),
                                                                  self.y + self.dot_size * (y + 2.5),
                                                                  batch=self.game.batch, group=groups.g[6])
        else:
            self.sprites[x][y].delete()
            self.sprites[x][y] = client_utility.sprite_with_scale(images.UnitSlot, self.dot_scale, 1, 1,
                                                                  self.x + self.dot_size * (x + 2.5),
                                                                  self.y + self.dot_size * (y + 2.5),
                                                                  batch=self.game.batch, group=groups.g[6])


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
        self.game.unit_formation.set_unit(x, y, None)


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
                if self.troops[x][y] is not None:
                    x_location = ((x - self.game.unit_formation_columns * .5) * UNIT_SIZE +
                                  self.game.players[self.game.side].TownHall.x) * SPRITE_SIZE_MULT - self.camx
                    y_location = ((y - self.game.unit_formation_rows * .5) * UNIT_SIZE +
                                  self.game.players[self.game.side].TownHall.y) * SPRITE_SIZE_MULT - self.camy
                    self.sprites.append(client_utility.sprite_with_scale(*possible_units[self.troops[x][y]].get_image(),
                                                                         x=x_location,
                                                                         y=y_location,
                                                                         group=groups.g[5],
                                                                         batch=self.game.batch))
        self.current_pos = [self.game.players[self.game.side].TownHall.x*SPRITE_SIZE_MULT, self.game.players[self.game.side].TownHall.y*SPRITE_SIZE_MULT]
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
            self.instructions.append(["walk", (x+self.camx)/SPRITE_SIZE_MULT,
                                      (y + self.camy)/SPRITE_SIZE_MULT])
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
        self.x, self.y = x, y
        self.side = side
        self.size = unit_stats[self.name]["size"]
        self.hp = unit_stats[self.name]["hp"]
        self.sprite = pyglet.sprite.Sprite(images.Intro, x=(x - self.size * .5) * SPRITE_SIZE_MULT,
                                           y=(y - self.size * .5) * SPRITE_SIZE_MULT, batch=game.batch,
                                           group=groups.g[2])
        self.sprite.scale = self.size * SPRITE_SIZE_MULT / self.sprite.width
        self.game = game

    def update_cam(self, x, y):
        self.sprite.update(x=(self.x - self.size * .5) * SPRITE_SIZE_MULT - x,
                           y=(self.y - self.size * .5) * SPRITE_SIZE_MULT - y)

    def tick(self):
        self.shove()

    def shove(self):
        for e in self.game.players[self.side - 1].units:
            if max(abs(e.x - self.x), abs(e.y - self.y)) < (self.size + e.size) / 2:
                dist_sq = (e.x - self.x) ** 2 + (e.y - self.y) ** 2
                if dist_sq < ((e.size + self.size) * .5) ** 2:
                    shovage = (e.size + self.size) * .5 * dist_sq ** -.5 - 1
                    e.take_knockback((e.x - self.x) * shovage, (e.y - self.y) * shovage, self)

    def graphics_update(self):
        pass


class Tower:
    name = "Tower"

    def __init__(self, ID, x, y, tick, side, game):
        self.x, self.y = x, y
        self.exists = False
        self.spawning = game.ticks - tick
        self.ID = ID
        self.side = side
        self.size = unit_stats[self.name]["size"]
        self.hp = unit_stats[self.name]["hp"]
        self.sprite = pyglet.sprite.Sprite(images.Tower, x=x * SPRITE_SIZE_MULT,
                                           y=y * SPRITE_SIZE_MULT, batch=game.batch,
                                           group=groups.g[2])
        self.sprite.scale = self.size * SPRITE_SIZE_MULT / self.sprite.width
        self.sprite.opacity = 70
        game.players[side].towers.append(self)
        game.players[side].all_buildings.append(self)
        self.game = game
        self.update_cam(self.game.camx, self.game.camy)

    def update_cam(self, x, y):
        self.sprite.update(x=self.x * SPRITE_SIZE_MULT - x, y=self.y * SPRITE_SIZE_MULT - y)

    def delete(self):
        self.game.players[self.side].towers.remove(self)
        self.game.players[self.side].all_buildings.remove(self)
        self.sprite.delete()

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
        for e in self.game.players[self.side - 1].units:
            if max(abs(e.x - self.x), abs(e.y - self.y)) < (self.size + e.size) / 2:
                dist_sq = (e.x - self.x) ** 2 + (e.y - self.y) ** 2
                if dist_sq < ((e.size + self.size) * .5) ** 2:
                    shovage = (e.size + self.size) * .5 * dist_sq ** -.5 - 1
                    e.take_knockback((e.x - self.x) * shovage, (e.y - self.y) * shovage, self)

    def graphics_update(self):
        pass


class Wall:
    name = "Wall"

    def __init__(self, ID, t1, t2, tick, side, game):
        self.exists = False
        self.spawning = game.ticks - tick
        self.ID = ID
        self.x1, self.y1, self.x2, self.y2 = t1.x, t1.y, t2.x, t2.y
        self.length = ((self.x1 - self.x2) ** 2 + (self.y1 - self.y2) ** 2) ** .5
        self.norm_vector = ((self.y2 - self.y1) / self.length, (self.x1 - self.x2) / self.length)
        self.line_c = -self.norm_vector[0] * self.x1 - self.norm_vector[1] * self.y1
        self.crossline_c = (-self.norm_vector[1] * (self.x1 + self.x2) + self.norm_vector[0] * (self.y1 + self.y2)) * .5
        self.side = side
        self.width = unit_stats[self.name]["width"]
        self.hp = unit_stats[self.name]["hp"]
        self.game = game
        game.players[side].walls.append(self)
        game.players[side].all_buildings.append(self)
        x = self.width * .5 / self.length
        a = x * (self.y2 - self.y1)
        b = x * (self.x1 - self.x2)
        self.texgroup = client_utility.TextureBindGroup(images.Wall, layer=1)
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        self.vertices_no_cam = [e * SPRITE_SIZE_MULT for e in [
            self.x1 - a, self.y1 - b, self.x1 + a, self.y1 + b, self.x2 + a, self.y2 + b, self.x2 - a, self.y2 - b]]
        self.sprite = game.batch.add(
            4, pyglet.gl.GL_QUADS, self.texgroup,
            ("v2f", self.vertices_no_cam),
            ("t2f", (0, 0, 1, 0, 1, 0.5 / x,
                     0, 0.5 / x)),
            ("c4B", (255, 255, 255, 70) * 4)
        )
        self.update_cam(self.game.camx, self.game.camy)

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
        self.sprite.vertices = [(self.vertices_no_cam[i] - (x if i % 2 == 0 else y)) for i in range(8)]

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
                if troops[column][row] is not None:
                    self.troops.append(
                        possible_units[troops[column][row]](
                            i,
                            (column - self.game.unit_formation_columns / 2) * UNIT_SIZE + self.x,
                            (row - self.game.unit_formation_rows / 2) * UNIT_SIZE + self.y,
                            side,
                            column - self.game.unit_formation_columns / 2,
                            row - self.game.unit_formation_rows / 2,
                            game
                        )
                    )
                    i += 1
        self.instr_object = instruction_moving(self, self.x, self.y)

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

    def delete(self):
        self.game.players[self.side].formations.remove(self)

    def update_cam(self, x, y):
        [e.update_cam(x, y) for e in self.troops]


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
        if False not in [e.reached_goal for e in self.target.troops]:
            if self.completed_rotate:
                self.completed = True
                self.target.x, self.target.y = self.x, self.y
                return
            self.completed_rotate = True
            [e.try_move(e.desired_x + self.dx, e.desired_y + self.dy) for e in self.target.troops]


class Unit:
    image = images.Cancelbutton
    name = "None"

    def __init__(self, ID, x, y, side, column, row, game):
        self.ID = ID
        self.side = side
        self.game = game
        self.x, self.y = x, y
        self.column, self.row = column, row
        self.game.players[self.side].units.append(self)
        self.sprite = client_utility.sprite_with_scale(self.image, unit_stats[self.name][
            "vwidth"] * SPRITE_SIZE_MULT / self.image.width,
                                                       1, 1, batch=game.batch, x=x * SPRITE_SIZE_MULT - game.camx,
                                                       y=y * SPRITE_SIZE_MULT - game.camy, group=groups.g[5])
        self.speed = unit_stats[self.name]["speed"] / FPS
        self.size = unit_stats[self.name]["size"]
        self.health = self.max_health = unit_stats[self.name]["hp"]
        self.damage = unit_stats[self.name]["dmg"]
        self.attack_cooldown = unit_stats[self.name]["cd"]
        self.sprite.opacity = 70
        self.exists = False
        self.rotation = 0
        self.desired_x, self.desired_y = x, y
        self.vx, self.vy = self.speed, 0
        self.reached_goal = True
        self.mass = 1

    def tick(self):
        pass

    def tick2(self):
        if self.reached_goal:
            return
        if self.y == self.desired_y and self.x == self.desired_x:
            self.reached_goal = True
            return
        if self.x <= self.desired_x:
            self.x += min(self.vx, self.desired_x - self.x)
        else:
            self.x += max(self.vx, self.desired_x - self.x)
        if self.y <= self.desired_y:
            self.y += min(self.vy, self.desired_y - self.y)
        else:
            self.y += max(self.vy, self.desired_y - self.y)
        #self.shove()

    def take_knockback(self, x, y, source):
        self.x += x
        self.y += y
        self.rotate(self.desired_x - self.x, self.desired_y - self.y)

    def rotate(self, x, y):
        if x == 0 == y:
            return
        inv_hypot = (x ** 2 + y ** 2) ** -.5
        if x >= 0:
            try:
                r = math.asin(y * inv_hypot)
            except:
                r = math.asin(max(min(y * inv_hypot, 1), -1))
        else:
            try:
                r = math.pi - math.asin(y * inv_hypot)
            except:
                r = math.pi - math.asin(max(min(y * inv_hypot, 1), -1))
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
        # disabled - too much lag
        for e in self.game.players[self.side - 1].units:
            if max(abs(e.x - self.x), abs(e.y - self.y)) > (self.size + e.size) / 2:
                continue
            dist_sq = (e.x - self.x) ** 2 + (e.y - self.y) ** 2
            if dist_sq < ((e.size + self.size) * .5) ** 2:
                shovage = (e.size + self.size) * .5 * dist_sq ** -.5 - 1
                mass_ratio = self.mass / e.mass
                ex, ey, selfx, selfy = e.x, e.y, self.x, self.y
                e.take_knockback((ex - selfx) * shovage * mass_ratio, (ey - selfy) * shovage * mass_ratio, self)
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
                e.take_knockback((ex - selfx) * shovage * mass_ratio, (ey - selfy) * shovage * mass_ratio, self)
                self.take_knockback((ex - selfx) * shovage * (mass_ratio - 1),
                                    (ey - selfy) * shovage * (mass_ratio - 1), self)

    def graphics_update(self):
        if self.exists:
            self.sprite.update(x=self.x * SPRITE_SIZE_MULT - self.game.camx,
                               y=self.y * SPRITE_SIZE_MULT - self.game.camy,
                               rotation=-self.rotation * 180 / math.pi + 90)

    @classmethod
    def get_image(cls):
        return [cls.image, unit_stats[cls.name]["vwidth"] * SPRITE_SIZE_MULT / cls.image.width, 1, 1]


class Swordsman(Unit):
    image = images.Swordsman
    name = "Swordsman"

    def __init__(self, ID, x, y, side, column, row, game):
        super().__init__(ID, x, y, side, column, row, game)


class selection_swordsman(selection_unit):
    image = images.gunmanR
    num = 0


possible_units = [Swordsman]
selects_p1 = [selection_tower, selection_wall]
selects_p2 = [selection_swordsman]
selects_all = [selects_p1, selects_p2]

# #################  ---/units---  #################
