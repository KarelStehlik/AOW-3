from imports import *
import groups
from constants import *
from client_utility import *
class Game():
    def __init__(self,side,batch):
        self.side,self.batch=side,batch
        self.players=[player(),player()]
        self.background_texgroup=TextureBindGroup(images.Background,layer=0)
        self.background=batch.add(
            4,pyglet.gl.GL_QUADS,self.background_texgroup,
            ("v2i",(0,0,SCREEN_WIDTH,0,
            SCREEN_WIDTH,SCREEN_HEIGHT,0,SCREEN_HEIGHT)),
            ("t2f",(0,0,SCREEN_WIDTH/512,0,SCREEN_WIDTH/512,SCREEN_HEIGHT/512,
                    0,SCREEN_HEIGHT/512))
        )
    def tick(self):
        self.players[0].tick()
        self.players[1].tick()
    def network(self,data):
        pass

class player():
    def __init__(self):
        self.walls=[]
        self.units=[]
        self.towers=[]
    def tick(self):
        [e.tick() for e in self.units]
        [e.tick for e in self.towers]
    def update_cam(x,y):
        [e.update_cam(x,y) for e in self.units]
        [e.update_cam(x,y) for e in self.towers]
        [e.update_cam(x,y) for e in self.walls]
