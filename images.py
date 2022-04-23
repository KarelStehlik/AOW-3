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


Testfire = RI("Testfire")
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
Smoke = RI("smoke")
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
Bowman = RI("Bowman", False)
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

# #######################  CLONE  ############################
gunmanR = pyglet.resource.image("imagefolder/BGunman.png")
gunmanG = pyglet.resource.image("imagefolder/GGunman.png")
engiR = pyglet.resource.image("imagefolder/BEngi.png")
engiG = pyglet.resource.image("imagefolder/GEngi.png")
turretR = pyglet.resource.image("imagefolder/BTurret.png")
turretG = pyglet.resource.image("imagefolder/GTurret.png")
mixerR = pyglet.resource.image("imagefolder/BMixer.png")
mixerG = pyglet.resource.image("imagefolder/GMixer.png")
megamixerR = pyglet.resource.image("imagefolder/BMegaMixer.png")
megamixerG = pyglet.resource.image("imagefolder/GMegaMixer.png")
teleG = pyglet.resource.image("imagefolder/GTele.png")
teleR = pyglet.resource.image("imagefolder/BTele.png")
ZookaG = pyglet.resource.image("imagefolder/GZooka.png")
ZookaR = pyglet.resource.image("imagefolder/BZooka.png")
ShieldG = pyglet.resource.image("imagefolder/GShield.png").get_transform(flip_x=True)
ShieldR = pyglet.resource.image("imagefolder/BShield.png").get_transform(flip_x=True)
sprayerR = pyglet.resource.image("imagefolder/BSprayer.png")
sprayerG = pyglet.resource.image("imagefolder/GSprayer.png")
flameR = pyglet.resource.image("imagefolder/BFlamethrower.png")
flameG = pyglet.resource.image("imagefolder/GFlamethrower.png")
JetIconTex = pyglet.image.load("imagefolder/JetIcon.png").get_texture()

earthquack = pyglet.resource.image("imagefolder/earthquack.png")
earthquack.anchor_x = earthquack.width // 2
SmashR = pyglet.resource.image("imagefolder/BSmash.png")
SmashG = pyglet.resource.image("imagefolder/GSmash.png")
SmashRL = pyglet.resource.image("imagefolder/BSmashL.png")
SmashGL = pyglet.resource.image("imagefolder/GSmashL.png")
SmashRR = pyglet.resource.image("imagefolder/BSmashR.png")
SmashGR = pyglet.resource.image("imagefolder/GSmashR.png")
jetR = pyglet.resource.image("imagefolder/BJet.png")
jetG = pyglet.resource.image("imagefolder/GJet.png")
for e in [SmashR, SmashG]:
    e.width = 80 * SPRITE_SIZE_MULT
    e.height = 120 * SPRITE_SIZE_MULT
    e.anchor_x = e.width // 2
for e in [SmashRL, SmashGL, SmashRR, SmashGR]:
    e.width = 100 * SPRITE_SIZE_MULT
    e.height = 120 * SPRITE_SIZE_MULT
for e in [SmashRR, SmashGR]:
    e.anchor_x = 40 * SPRITE_SIZE_MULT
for e in [SmashRL, SmashGL]:
    e.anchor_x = 60 * SPRITE_SIZE_MULT

MSmashR = pyglet.resource.image("imagefolder/BMSmash.png")
MSmashG = pyglet.resource.image("imagefolder/GMSmash.png")
MSmashRL = pyglet.resource.image("imagefolder/BMSmashL.png")
MSmashGL = pyglet.resource.image("imagefolder/GMSmashL.png")
MSmashRR = pyglet.resource.image("imagefolder/BMSmashR.png")
MSmashGR = pyglet.resource.image("imagefolder/GMSmashR.png")
for e in [MSmashR, MSmashG]:
    e.width = 117 * SPRITE_SIZE_MULT
    e.height = 150 * SPRITE_SIZE_MULT
    e.anchor_x = e.width // 2
for e in [MSmashRL, MSmashGL, MSmashRR, MSmashGR]:
    e.width = 125 * SPRITE_SIZE_MULT
    e.height = 150 * SPRITE_SIZE_MULT
for e in [MSmashRR, MSmashGR]:
    e.anchor_x = 50 * SPRITE_SIZE_MULT
for e in [MSmashRL, MSmashGL]:
    e.anchor_x = 75 * SPRITE_SIZE_MULT

tankR = pyglet.resource.image("imagefolder/BTank.png")
tankG = pyglet.resource.image("imagefolder/GTank.png")
for e in [tankR, tankG]:
    e.width = 250
    e.height = 90
    e.anchor_x = 60

flameG.width = 65 * SPRITE_SIZE_MULT
flameG.height = 90 * SPRITE_SIZE_MULT
flameR.width = 65 * SPRITE_SIZE_MULT
flameR.height = 90 * SPRITE_SIZE_MULT
flameG.anchor_x = flameR.anchor_x = 30 * SPRITE_SIZE_MULT

jetG.width = 160 * SPRITE_SIZE_MULT
jetG.height = 130 * SPRITE_SIZE_MULT
jetR.width = 160 * SPRITE_SIZE_MULT
jetR.height = 130 * SPRITE_SIZE_MULT
jetG.anchor_x = jetR.anchor_x = 80 * SPRITE_SIZE_MULT
jetG.anchor_y = jetR.anchor_y = 65 * SPRITE_SIZE_MULT

sprayerG.width = 60 * SPRITE_SIZE_MULT
sprayerG.height = 80 * SPRITE_SIZE_MULT
sprayerR.width = 60 * SPRITE_SIZE_MULT
sprayerR.height = 80 * SPRITE_SIZE_MULT

gunmanG.width = 40 * SPRITE_SIZE_MULT
gunmanG.height = 70 * SPRITE_SIZE_MULT
gunmanR.width = 40 * SPRITE_SIZE_MULT
gunmanR.height = 70 * SPRITE_SIZE_MULT

engiG.width = 40 * SPRITE_SIZE_MULT
engiG.height = 70 * SPRITE_SIZE_MULT
engiR.width = 40 * SPRITE_SIZE_MULT
engiR.height = 70 * SPRITE_SIZE_MULT

turretG.width = 60 * SPRITE_SIZE_MULT
turretG.height = 54 * SPRITE_SIZE_MULT
turretR.width = 60 * SPRITE_SIZE_MULT
turretR.height = 54 * SPRITE_SIZE_MULT
turretG.anchor_x = 15
turretR.anchor_x = 15

mixerG.width = 35 * SPRITE_SIZE_MULT
mixerG.height = 60 * SPRITE_SIZE_MULT
mixerR.width = 35 * SPRITE_SIZE_MULT
mixerR.height = 60 * SPRITE_SIZE_MULT

megamixerG.width = 75 * SPRITE_SIZE_MULT
megamixerG.height = 125 * SPRITE_SIZE_MULT
megamixerR.width = 75 * SPRITE_SIZE_MULT
megamixerR.height = 125 * SPRITE_SIZE_MULT

teleG.width = 50 * SPRITE_SIZE_MULT
teleG.height = 80 * SPRITE_SIZE_MULT
teleR.width = 50 * SPRITE_SIZE_MULT
teleR.height = 80 * SPRITE_SIZE_MULT

ZookaG.anchor_x = 55 * SPRITE_SIZE_MULT
ZookaG.width = 200 * SPRITE_SIZE_MULT
ZookaG.height = 68 * SPRITE_SIZE_MULT

ZookaR.anchor_x = 55 * SPRITE_SIZE_MULT
ZookaR.width = 200 * SPRITE_SIZE_MULT
ZookaR.height = 68 * SPRITE_SIZE_MULT

ShieldG.width = 70 * SPRITE_SIZE_MULT
ShieldR.width = 70 * SPRITE_SIZE_MULT
ShieldG.height = 110 * SPRITE_SIZE_MULT
ShieldR.height = 110 * SPRITE_SIZE_MULT
ShieldG.anchor_x = 20 * SPRITE_SIZE_MULT
ShieldR.anchor_x = 20 * SPRITE_SIZE_MULT

gunmanG.anchor_x -= 5 * SPRITE_SIZE_MULT
gunmanR.anchor_x -= 5 * SPRITE_SIZE_MULT

bullet = pyglet.resource.image("imagefolder/Bullet.png")
bullet.width = bullet.height = 6 * SPRITE_SIZE_MULT
bullet.anchor_x = bullet.anchor_y = 3 * SPRITE_SIZE_MULT

BazookaBullet = pyglet.resource.image("imagefolder/BazookaBullet.png")
BazookaBullet.width = int(BazookaBullet.width * SPRITE_SIZE_MULT / 15)
BazookaBullet.height = int(BazookaBullet.height * SPRITE_SIZE_MULT / 15)
centre_anchor(BazookaBullet)

Grenade = pyglet.resource.image("imagefolder/Grenade.png")
Grenade.width = int(25 * SPRITE_SIZE_MULT)
Grenade.height = int(40 * SPRITE_SIZE_MULT)
Grenade.anchor_x = Grenade.width // 2

buttonG = pyglet.image.load("imagefolder/GreenButton.png")
buttonR = pyglet.image.load("imagefolder/RedButton.png")
platform = pyglet.resource.image("imagefolder/platform.png")
platform.width = int(platform.width * SPRITE_SIZE_MULT)
platform.height = int(platform.height * SPRITE_SIZE_MULT)
platform.anchor_x = platform.anchor_y = 0
cloneFrame = pyglet.resource.image("imagefolder/clone_select.png")
cloneFrame.height *= SPRITE_SIZE_MULT
cloneFrame.width *= SPRITE_SIZE_MULT
red_arrow = pyglet.resource.image("imagefolder/red_arrow.png")
red_arrow.anchor_x = int(red_arrow.width / 2)
