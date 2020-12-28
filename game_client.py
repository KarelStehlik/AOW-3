from imports import *
import groups
from constants import *
from client_utility import *
class test():
    def __init__(self,x,y):
        self.x=x
        self.y=y
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
        self.UI_bottomBar=UI_bottom_bar(self)
        self.UI_toolbars=[self.UI_bottomBar]
        self.selected=selection(self)
    def select(self,sel):
        self.selected.end()
        self.selected=sel(self)
    def tick(self):
        self.players[0].tick()
        self.players[1].tick()
    def network(self,data):
        if "action" in data:
            if data["action"]=="place_tower":
                Tower(data["ID"],data["xy"][0],data["xy"][1],data["side"],self)
            elif data["action"]=="place_wall":
                Wall(data["ID"],self.find_tower(data["ID1"],data["side"]),
                     self.find_tower(data["ID2"],data["side"]),data["side"],self)
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
    def find_tower(self,ID,side):
        for e in self.players[side].towers:
            if e.ID==ID:
                return e
        return None
    def find_wall(self,ID,side):
        for e in self.players[side].walls:
            if e.ID==ID:
                return e
        return None
    def find_unit(self,ID,side):
        for e in self.players[side].units:
            if e.ID==ID:
                return e
        return None

class UI_bottom_bar(toolbar):
    def __init__(self,game):
        super().__init__(0,0,SCREEN_WIDTH,SCREEN_HEIGHT/5,game.batch)
        self.game=game
        self.page=0
        self.load_page(0)
    def load_page(self,n):
        i=0
        for e in selects_all[n]:
            self.add(self.game.select,SCREEN_WIDTH*(0.01+0.1*i),SCREEN_WIDTH*0.01,
                     SCREEN_WIDTH*0.09,SCREEN_WIDTH*0.09,e.img,args=(e,))
            i+=1
    def unload_page(self):
        [e.delete() for e in self.buttons]

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

##################   ---/core---  #################
##################  ---selects---  #################
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
    img=images.Towerbutton
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

class selection_wall(selection):
    img=images.Towerbutton
    def __init__(self,game):
        self.game=game
        self.cancelbutton=button(self.end,SCREEN_WIDTH*0.01,SCREEN_HEIGHT*0.9,
                                 SCREEN_WIDTH*0.1,SCREEN_HEIGHT*0.09,game.batch,
                                 image=images.Cancelbutton)
        self.selected1,self.selected1=None,None
        self.buttons=[]
        for e in game.players[game.side].towers:
            self.buttons.append(button(self.select,e.x-20,e.y-20,40,40,
                                       self.game.batch,args=(e.ID,)))
        self.sprite=None
    def select(self,ID):
        if self.selected1==None or self.selected1==ID:
            self.selected1=ID
            return
        self.selected2=ID
        self.game.connection.Send({"action":"place_wall","ID1":self.selected1,
                                   "ID2":self.selected2})
        self.end()
    def mouse_move(self,x,y):
        pass
    def mouse_click(self,x,y):
        if not self.cancelbutton.mouse_click(x,y):
            [e.mouse_click(x,y) for e in self.buttons]
    def mouse_release(self,x,y):
        self.cancelbutton.mouse_release(x,y)
        [e.mouse_release(x,y) for e in self.buttons]
    def end(self):
        self.game.selected=selection(self.game)
        self.cancelbutton.delete()
        [e.delete() for e in self.buttons]

selects_p1=[selection_tower,selection_wall]
selects_all=[selects_p1]

################## ---/selects--- #################
##################   ---units---  #################   

class Tower():
    name="Tower"
    def __init__(self,ID,x,y,side,game):
        self.x,self.y=x,y
        self.ID=ID
        self.side=side
        self.size=unit_stats[self.name]["size"]
        self.sprite=pyglet.sprite.Sprite(images.Intro,x=x-self.size/2,
                                         y=y-self.size/2,batch=game.batch,
                                         group=groups.g[2])
        self.sprite.scale=self.size/self.sprite.width
        self.l=game.players[side].towers
        self.l.append(self)
        self.game=game
    def tick(self):
        pass
    def delete(self):
        self.l.remove(self)
        self.sprite.delete()

class Wall():
    name="Wall"
    def __init__(self,ID,t1,t2,side,game):
        self.ID=ID
        self.x1,self.y1,self.x2,self.y2=t1.x,t1.y,t2.x,t2.y
        self.side=side
        self.width=unit_stats[self.name]["width"]
        self.game=game
        self.l=game.players[side].walls
        self.l.append(self)
        x=self.width/2/math.sqrt((self.x1-self.x2)**2+(self.y1-self.y2)**2)
        a=x*(self.y2-self.y1)
        b=x*(self.x1-self.x2)
        self.texgroup=TextureBindGroup(images.JetIconTex,layer=1)
        glEnable(GL_BLEND)
        self.sprite=game.batch.add(
            4,pyglet.gl.GL_QUADS,self.texgroup,
            ("v2f",(self.x1-a,self.y1-b,self.x1+a,self.y1+b,
            self.x2+a,self.y2+b,self.x2-a,self.y2-b)),
            ("t2f",(0,0,1,0,1,0.5/x,
                    0,0.5/x))
        )

##################  ---/units---  #################
