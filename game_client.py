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
        self.unit_formation_rows = 10
        self.unit_formation_columns = 20
        self.unit_formation = UI_formation(self)
        self.UI_toolbars = [self.UI_bottomBar, self.UI_categories, self.unit_formation]
        self.selected = selection_none(self)

    def select(self, sel):
        self.selected.end()
        self.selected = sel(self)

    def tick(self):
        while self.ticks < FPS * (time.time() - self.start_time):
            self.players[0].tick()
            self.players[1].tick()
            self.ticks += 1
        self.update_cam()
        self.batch.draw()

    def network(self, data):
        if "action" in data:
            if data["action"] == "place_tower":
                Tower(data["ID"], data["xy"][0], data["xy"][1], data["tick"], data["side"], self)
            elif data["action"] == "place_wall":
                Wall(data["ID"], self.find_tower(data["ID1"], data["side"]),
                     self.find_tower(data["ID2"], data["side"]), data["tick"], data["side"], self)

    def mouse_move(self, x, y, dx, dy):
        [e.mouse_move(x, y) for e in self.UI_toolbars]
        self.selected.mouse_move(x, y)

    def mouse_drag(self, x, y, dx, dy, button, modifiers):
        pass

    def key_press(self, symbol, modifiers):
        if symbol == key.A:
            self.camx_moving = max(self.camx_moving - self.cam_move_speed, -self.cam_move_speed)
        elif symbol == key.S:
            self.camy_moving = max(self.camy_moving - self.cam_move_speed, -self.cam_move_speed)
        elif symbol == key.D:
            self.camx_moving = min(self.camx_moving + self.cam_move_speed, self.cam_move_speed)
        elif symbol == key.W:
            self.camy_moving = min(self.camy_moving + self.cam_move_speed, self.cam_move_speed)

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
        super().__init__(SCREEN_WIDTH - self.dot_size * (self.columns + 4), 0, self.dot_size * (self.columns + 4),
                         self.dot_size * (self.rows + 4), game.batch, image=images.UnitFormFrame, layer=5)
        self.units = [[None for _ in range(self.rows)] for _ in range(self.columns)]
        self.Buttons2d = [[self.add(self.clicked, SCREEN_WIDTH + self.dot_size * (x - self.columns - 2),
                                    self.dot_size * (y + 2), self.dot_size, self.dot_size,
                                    image=images.UnitSlot, args=(x, y)) for y in range(self.rows)] for x in
                          range(self.columns)]
        self.add(self.send, SCREEN_WIDTH - self.dot_size * (self.columns + 4), 0, SCREEN_WIDTH / 5, SCREEN_HEIGHT / 5,
                 image=images.Cancelbutton)

    def clicked(self, x, y):
        self.game.selected.clicked_unit_slot(x, y)

    def send(self):
        self.game.select(selection_unit)

    def set_unit(self, x, y, num):
        self.units[x][y] = num
        if num is None:
            self.Buttons2d[x][y].set_image(images.UnitSlot)
        else:
            self.Buttons2d[x][y].set_image(possible_units[num].image)


class UI_categories(client_utility.toolbar):
    def __init__(self, game, bb):
        super().__init__(0, bb.height, SCREEN_WIDTH, SCREEN_HEIGHT * 0.05, game.batch)
        i = 0
        for _ in selects_all:
            self.add(bb.load_page, SCREEN_WIDTH * (0.01 + 0.1 * i), bb.height + SCREEN_HEIGHT * 0.005,
                     SCREEN_WIDTH * 0.09, SCREEN_HEIGHT * 0.04, args=(i,))
            i += 1


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

    def update_cam(self, x, y):
        [e.update_cam(x, y) for e in self.units]
        [e.update_cam(x, y) for e in self.all_buildings]


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

    def mouse_click(self, x, y):
        pass

    def mouse_release(self, x, y):
        pass

    def end(self):
        self.game.selected = selection_none(self.game)
        self.cancelbutton.delete()

    def update_cam(self, x, y):
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
            self.game.connection.Send({"action": "place_tower", "xy": [x + self.camx, y + self.camy]})
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
            self.buttons.append(client_utility.button(self.select, e.x - 20, e.y - 20, 40, 40,
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
        [e.mouse_release(x, y) for e in self.buttons]

    def end(self):
        super().end()
        [e.delete() for e in self.buttons]

    def update_cam(self, x, y):
        [e.update(e.ogx - x, e.ogy - y) for e in self.buttons]
        self.camx, self.camy = x, y


class selection_unit(selection):
    img = images.gunmanR

    def __init__(self, game):
        super().__init__(game)
        self.troops = self.game.unit_formation.units
        self.sprites = [[client_utility.sprite_with_scale(*possible_units[self.troops[x][y]].get_image(),
                                                          x=x * UNIT_SIZE,
                                                          y=y * UNIT_SIZE)
                         for y in range(self.game.unit_formation_rows)]
                        for x in range(self.game.unit_formation_columns)]

    def mouse_move(self, x, y):
        pass

    def mouse_click(self, x, y):
        if not self.cancelbutton.mouse_click(x, y):
            pass

    def mouse_release(self, x, y):
        self.cancelbutton.mouse_release(x, y)

    def end(self):
        super().end()

    def update_cam(self, x, y):
        pass

    def clicked_unit_slot(self, x, y):
        self.game.unit_formation.set_unit(x, y, 0)


selects_p1 = [selection_tower, selection_wall]
selects_p2 = [selection_unit]
selects_all = [selects_p1, selects_p2]


# ################# ---/selects--- #################
# #################   ---units---  #################

class TownHall:
    name = "TownHall"

    def __init__(self, x, y, side, game):
        self.x, self.y = x, y
        self.side = side
        self.size = unit_stats[self.name]["size"]
        self.hp = unit_stats[self.name]["hp"]
        self.sprite = pyglet.sprite.Sprite(images.Intro, x=x - self.size / 2,
                                           y=y - self.size / 2, batch=game.batch,
                                           group=groups.g[2])
        self.sprite.scale = self.size / self.sprite.width
        self.game = game

    def update_cam(self, x, y):
        self.sprite.update(x=self.x - self.size / 2 - x, y=self.y - self.size / 2 - y)

    def tick(self):
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
        self.sprite = pyglet.sprite.Sprite(images.Intro, x=x - self.size / 2,
                                           y=y - self.size / 2, batch=game.batch,
                                           group=groups.g[2])
        self.sprite.scale = self.size / self.sprite.width
        self.sprite.opacity = 70
        game.players[side].towers.append(self)
        game.players[side].all_buildings.append(self)
        self.game = game
        self.update_cam(self.game.camx, self.game.camy)
        self.spinspeed = 600 / FPS

    def update_cam(self, x, y):
        self.sprite.update(x=self.x - self.size / 2 - x, y=self.y - self.size / 2 - y)

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
        self.sprite.rotation += self.spinspeed


class Wall:
    name = "Wall"

    def __init__(self, ID, t1, t2, tick, side, game):
        self.exists = False
        self.spawning = game.ticks - tick
        self.ID = ID
        self.x1, self.y1, self.x2, self.y2 = t1.x, t1.y, t2.x, t2.y
        self.side = side
        self.width = unit_stats[self.name]["width"]
        self.hp = unit_stats[self.name]["hp"]
        self.game = game
        game.players[side].walls.append(self)
        game.players[side].all_buildings.append(self)
        x = self.width / 2 / math.sqrt((self.x1 - self.x2) ** 2 + (self.y1 - self.y2) ** 2)
        a = x * (self.y2 - self.y1)
        b = x * (self.x1 - self.x2)
        self.texgroup = client_utility.TextureBindGroup(images.Wall, layer=1)
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        self.vertices_no_cam = (
            self.x1 - a, self.y1 - b, self.x1 + a, self.y1 + b, self.x2 + a, self.y2 + b, self.x2 - a, self.y2 - b)
        self.sprite = game.batch.add(
            4, pyglet.gl.GL_QUADS, self.texgroup,
            ("v2f", self.vertices_no_cam),
            ("t2f", (0, 0, 1, 0, 1, 0.5 / x,
                     0, 0.5 / x)),
            ("c4B", (255, 255, 255, 70) * 4)
        )
        self.update_cam(self.game.camx, self.game.camy)

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
        pass


class Formation:
    def __init__(self, ID, plan, side, game):
        self.ID = ID
        self.plan = plan
        self.side = side
        self.game = game


class Unit:
    image = images.Cancelbutton
    name = "None"

    def __init__(self, ID, side, game):
        self.ID = ID
        self.side = side
        self.game = game

    @classmethod
    def get_image(cls):
        return [unit_stats[cls.name]["vwidth"] / cls.image.width, 1, 1, cls.image]


class Swordsman(Unit):
    image = images.gunmanG
    name = "Swordsman"

    def __init__(self, ID, side, game):
        super().__init__(ID, side, game)


possible_units = [Swordsman]

# #################  ---/units---  #################
