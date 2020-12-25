from imports import *
import groups
from constants import *
from client_utility import *

class Game():
    def __init__(self,side,batch,connection):
        self.side,self.batch=side,batch
        self.players=[player(),player()]
        self.connection=connection
        self.batch=batch
        self.background_texgroup=TextureBindGroup(images.Background,layer=0)
        self.background=batch.add(
            4,pyglet.gl.GL_QUADS,self.background_texgroup,
            ("v2i",(0,0,SCREEN_WIDTH,0,
            SCREEN_WIDTH,SCREEN_HEIGHT,0,SCREEN_HEIGHT)),
            ("t2f",(0,0,SCREEN_WIDTH/512,0,SCREEN_WIDTH/512,SCREEN_HEIGHT/512,
                    0,SCREEN_HEIGHT/512))
        )
        self.UI_toolbars=[]
        self.UI_bottomBar=toolbar(0,0,SCREEN_WIDTH,SCREEN_HEIGHT/5,self.batch)
        self.UI_toolbars.append(self.UI_bottomBar)
        self.UI_bottomBar.add(self.select_tower,20,20,100,100,image=images.Towerbutton)
        self.selected=selection(self)
    def select_tower(self):
        self.selected=selection_tower(self)
    def tick(self):
        self.players[0].tick()
        self.players[1].tick()
    def network(self,data):
        if "action" in data:
            if data["action"]=="place_tower":
                Tower(data["xy"][0],data["xy"][1],data["side"],self)
    def mouse_move(self,x, y, dx, dy):
        [e.mouse_move(x,y) for e in self.UI_toolbars]
        self.selected.mouse_move(x,y)
    def mouse_drag(self,x, y, dx, dy, button, modifiers):
        pass
    def key_press(self,symbol,modifiers):
        pass
    def key_release(self,symbol,modifiers):
        pass
    def mouse_press(self,x,y,button,modifiers):
        if not self.UI_bottomBar.mouse_click(x,y):
            self.selected.mouse_click(x,y)
    def mouse_release(self,x,y,button,modifiers):
        [e.mouse_release(x,y) for e in self.UI_toolbars]
        self.selected.mouse_release(x,y)
    def mouse_scroll(self, x, y, scroll_x, scroll_y):
        pass

class selection():
    def __init__(self,game):
        pass
    def mouse_move(self,x,y):
        pass
    def mouse_click(self,x,y):
        pass
    def mouse_release(self,x,y):
        pass
    def end(self):
        pass

class selection_tower(selection):
    def __init__(self,game):
        self.game=game
        self.size=unit_stats["Tower"]["size"]
        self.sprite=pyglet.sprite.Sprite(images.Intro,x=0,
                                         y=0,batch=game.batch,
                                         group=groups.g[2])
        self.sprite.scale=self.size/self.sprite.width
        self.sprite.opacity=100
        self.cancelbutton=button(self.end,SCREEN_WIDTH*0.01,SCREEN_HEIGHT*0.9,
                                 SCREEN_WIDTH*0.1,SCREEN_HEIGHT*0.09,game.batch,
                                 image=images.Cancelbutton)
    def mouse_move(self,x,y):
        self.sprite.update(x=x-self.size/2,y=y-self.size/2)
        self.cancelbutton.mouse_move(x,y)
    def mouse_click(self,x,y):
        if not self.cancelbutton.mouse_click(x,y):
            self.game.connection.Send({"action":"place_tower","xy":[x,y]})
            self.end()
    def mouse_release(self,x,y):
        self.cancelbutton.mouse_release(x,y)
    def end(self):
        self.game.selected=selection(self.game)
        self.sprite.delete()
        self.cancelbutton.delete()

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

class Tower():
    name="Tower"
    def __init__(self,x,y,side,game):
        self.x,self.y=x,y
        self.side=side
        self.size=unit_stats[self.name]["size"]
        self.sprite=pyglet.sprite.Sprite(images.Intro,x=x-self.size/2,
                                         y=y-self.size/2,batch=game.batch,
                                         group=groups.g[2])
        self.sprite.scale=self.size/self.sprite.width
        self.l=game.players[side].towers
        self.l.append(self)
    def tick(self):
        pass
