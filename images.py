from constants import *


def RI(name, centre=True):
    a = pyglet.resource.image(f"imagefolder/{name}.png")
    if centre:
        centre_anchor(a)
    return a


def IL(name, centre=True):
    a = pyglet.image.load(f"imagefolder/{name}.png")
    if centre:
        centre_anchor(a)
    return a


def centre_anchor(e):
    e.anchor_x = e.width // 2
    e.anchor_y = e.height // 2


def load_animation(folder, num, duration, name="/t", loop=False):
    images = [RI(folder + name + str(i)) for i in range(num)]
    return pyglet.image.Animation.from_image_sequence(images, duration, loop)


class anim_texture:
    def __init__(self, filename, rotations, frames):
        self.rotations = rotations
        self.frames = frames
        self.images = []
        for frame in range(frames):
            for rotation in range(rotations):
                self.images.append(IL(f"{filename}_{rotation}_{frame}").get_texture())

    def get_texture(self,rotation,frame):
        return self.images[frame*self.rotations+rotation]

    @property
    def width(self):
        return self.images[0].width


flame_wave = load_animation("flame_wave", 45, 1 / 10)
Explosion = load_animation("boom biatch", 25, 1 / 5, loop=True)
Explosion1 = load_animation("explosion", 98, 1 / 15, name="/tt")
Explosion2 = load_animation("explosion2", 104, 1 / 15, name="/t")
Background = IL("Background").get_texture()
Wall = IL("Wall").get_texture()
Mountain = IL("Boulder").get_texture()
WallCrack = IL("wall_crack").get_texture()
blue_arrow = IL("blue_arrow").get_texture()
Beam = IL("beam").get_texture()
Crater = RI("crater")
Tree = RI("tree")
MagicTree = RI("magic_tree")
Nature = RI("nature")
Fireball = load_animation("fireball", 151, 1 / 20, name="/t", loop=True)

Freeze = RI("Freeze")
Glow = RI("faura")
UpgradeButton = RI("UpgradeButton")
Rage = RI("Rage")
RageIcon = RI("Rage_Icon")
Warn = RI("Warn")
UpgradeLine = RI("UpgradeLine")
Egg = RI('Egg')
Button = RI("Button")
TargetButton = RI("TargetButton")
Toolbar = RI("Toolbar", False)
Intro = RI("Intro", False)
UpgradeScreen = RI("UpgradeScreen", False)
UpgradeCircle = RI("UpgradeCircle")
Cancelbutton = RI("Cancelbutton")
Sendbutton = RI("Sendbutton")
Towerbutton = RI("Towerbutton")
UnitSlot = RI("UnitSlot")
UnitFormFrame = RI("UnitFormFrame", False)
Fire = RI("fire")
Shockwave = RI("shockwave")
Boulder = RI("Boulder")
Meteor = RI("Meteor")
Meteor.anchor_x = Meteor.width / 2
Meteor.anchor_y = Meteor.height * .7
Bullet = RI("Bullet")
Arrow_upg = RI("Arrow_upg")
Arrow_upg_2 = RI("Arrow_upg_2")
Mine = RI("mine")
Chestplates = RI("Chestplates")

Farm = RI("farm")
Farm1 = RI("Farm1")
Farm11 = RI("Farm11")
Farm2 = RI("Farm2")
Farm21 = RI("Farm21")
Tower = RI("Tower")
Tower1 = RI("Tower1")
Tower3 = RI("Tower3")
Tower4 = RI("Tower4")
Tower31 = RI("Tower31")
Tower41 = RI("Tower41")
Tower221 = RI("Tower221")
Turret = RI("Turret")
Tower2 = RI("Tower2")
TowerCrack = RI("tower_crack")
Tower11 = RI("Tower11")
Tower21 = RI("Tower21")
Townhall = RI("Townhall")
Tower22 = RI("tower22")
Tower23 = RI("Tower23")

Arrow = RI("Arrow")
Arrow.anchor_x = Arrow.width / 2
Arrow.anchor_y = Arrow.height

Swordsman = RI("Swordsman", False)
Swordsman.anchor_x = 64
Swordsman.anchor_y = 54
Mancatcher = RI("Mancatcher")
Mancatcher.anchor_y = 100
Bowman = RI("Bowman", False)
Crab = RI("crab")
Bowman.anchor_x = 64
Bowman.anchor_y = 60
Trebuchet = RI("Trebuchet")
Trebuchet.anchor_x = Trebuchet.width / 2
Trebuchet.anchor_y = Trebuchet.height * .6
Defender = RI("Defender")
Bear = RI("Bear")
Necromancer = RI("Necromancer")
Zombie = RI("Zombie")
Golem = RI("Golem")