from PodSixNet.Connection import connection,ConnectionListener
from imports import *
from constants import *
import groups
pyglet.gl.glEnable(GL_BLEND)
connection.DoConnect(('192.168.1.132', 5071))
class MyNetworkListener(ConnectionListener):
    def __init__(self,*args,**kwargs):
        super().__init__()
        self.start=False
        self.mode=None
    def set_mode(self,m):
        self.mode=m
    def Network(self,data):
        print(data)
        self.mode.network(data)
nwl=MyNetworkListener()

class mode():
    def __init__(self,win,batch):
        self.batch=batch
        self.mousex=self.mousey=0
        self.win=win
    def mouse_move(self,x, y, dx, dy):
        self.mousex=x
        self.mousey=y
    def mouse_drag(self,x, y, dx, dy, button, modifiers):
        self.mouse_move(x,y,dx,dy)
    def tick(self,dt):
        pass
    def key_press(self,symbol,modifiers):
        pass
    def key_release(self,symbol,modifiers):
        pass
    def resize(self,width,height):
        pass
    def mouse_press(self,x,y,button,modifiers):
        pass
    def mouse_release(self,x,y,button,modifiers):
        pass
    def mouse_scroll(self, x, y, scroll_x, scroll_y):
        pass

class button():
    def __init__(self,func,x,y,width,height,batch,image=images.Button,text=""):
        self.sprite=pyglet.sprite.Sprite(image,x=x,y=y,batch=batch,group=groups.g[5])
        self.sprite.scale_x=width/self.sprite.width
        self.sprite.scale_y=height/self.sprite.height
        self.func=func
        self.x,self.y,self.width,self.height=x,y,width,height
        self.text=pyglet.text.Label(text,x=self.x+self.width//2,
                y=self.y+self.height*4/7,color=(255,255,0,255),
                batch=batch,group=groups.g[6],font_size=int(SPRITE_SIZE_MULT*self.height/2),
                anchor_x="center",align="center",anchor_y="center")
        self.down=False
    def mouse_click(self,x,y):
        if self.x+self.width>=x>=self.x and self.y+self.height>=y>=self.y:
            self.down=True
            self.sprite.scale=1.2
            self.sprite.update(x=self.x-self.width/10,y=self.y-self.height/10)
            return True
        return False
    def mouse_release(self,x,y):
        if self.down:
            self.down=False
            self.sprite.scale=1
            self.sprite.update(x=self.x,y=self.y)
            if self.x+self.width>=x>=self.x and self.y+self.height>=y>=self.y:
                self.func()
    def delete(self):
        self.sprite.delete()
        self.text.delete()

class mode_intro(mode):
    def __init__(self,win,batch,nwl):
        super().__init__(win,batch)
        nwl.set_mode(self)
        self.buttons=[]
        self.buttons.append(button(self.join,SCREEN_WIDTH*2/5,SCREEN_HEIGHT/3,
                                   SCREEN_WIDTH*1/5,SCREEN_HEIGHT/7,batch,text="Play"))
        self.bg=pyglet.sprite.Sprite(images.Intro,x=0,y=0,group=groups.g[0],batch=batch)
        self.bg.scale_x,self.bg.scale_y=SCREEN_WIDTH/self.bg.width,SCREEN_HEIGHT/self.bg.height
        self.joined=False
    def mouse_press(self,x,y,button,modifiers):
        [e.mouse_click(x,y) for e in self.buttons]
    def mouse_release(self,x,y,button,modifiers):
        [e.mouse_release(x,y) for e in self.buttons]
    def join(self):
        if not self.joined:
            connection.Send({"action":"join"})
            self.joined=True
    def mouse_drag(self,x, y, dx, dy, button, modifiers):
        self.mouse_move(x,y,dx,dy)
    def tick(self,dt):
        super().tick(dt)
    def end(self):
        self.bg.delete()
        while len(self.buttons)>=1:
            self.buttons.pop(0).delete()
    def network(self,data):
        if "action" in data and data["action"]=="start_game":
            newgame=Game(data["side"])
            self.end()
            self.win.start_game(newgame)

class TextureEnableGroup(pyglet.graphics.Group):
    def set_state(self):
        glEnable(GL_TEXTURE_2D)
    def unset_state(self):
        glDisable(GL_TEXTURE_2D)
texture_enable_group = TextureEnableGroup()

class TextureBindGroup(pyglet.graphics.Group):
    def __init__(self, texture):
        super(TextureBindGroup, self).__init__(parent=texture_enable_group)
        self.texture = texture
    def set_state(self):
        glBindTexture(GL_TEXTURE_2D, self.texture.id)
    # No unset_state method required.
    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.texture.id == other.texture.id and
                self.texture.target == other.texture.target and
                self.parent == other.parent)
    def __hash__(self):
        return hash((self.texture.id, self.texture.target))

class mode_main(mode):
    def __init__(self,win,batch,nwl,game):
        super().__init__(win,batch)
        nwl.set_mode(self)
        self.game=game
        self.background_texgroup=TextureBindGroup(images.Background)
        self.background=batch.add(
            4,pyglet.gl.GL_QUADS,self.background_texgroup,
            ("v2i",(0,0,SCREEN_WIDTH,0,
            SCREEN_WIDTH,SCREEN_HEIGHT,0,SCREEN_HEIGHT)),
            ("t2f",(0,0,SCREEN_WIDTH/512,0,SCREEN_WIDTH/512,SCREEN_HEIGHT/512,
                    0,SCREEN_HEIGHT/512))
        )
    def mouse_drag(self,x, y, dx, dy, button, modifiers):
        self.mouse_move(x,y,dx,dy)
    def tick(self,dt):
        super().tick(dt)
    def network(self,data):
        pass

class Game():
    def __init__(self, side):
        self.side=side
        self.buildings=[[],[]]
        self.units=[[],[]]
    def tick(self):
        pass
    def network(self):
        pass

class windoo(pyglet.window.Window):
    def start(self):
        self.nwl=nwl
        self.batch = pyglet.graphics.Batch()
        self.sec=self.frames=0
        self.fpscount=pyglet.text.Label(x=5,y=5,text="0",color=(255,255,255,255),
                                        group=groups.g[5],batch=self.batch)
        self.mouseheld=False
        self.current_mode=mode_intro(self,self.batch,self.nwl)
        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)
    def start_game(self,game):
        self.current_mode=mode_main(self,self.batch,self.nwl,game)
    def on_mouse_motion(self,x, y, dx, dy):
        self.current_mode.mouse_move(x,y,dx,dy)
    def on_mouse_drag(self,x,y,dx,dy,button,modifiers):
        self.current_mode.mouse_drag(x,y,dx,dy,button,modifiers)
    def on_close(self):
        self.close()
        connection.close()
        os._exit(0)
    def tick(self,dt):
        self.dispatch_events()
        self.check(dt)
        self.current_mode.tick(dt)
        self.switch_to()
        self.clear()
        self.batch.draw()
        self.flip()
    def on_key_press(self,symbol,modifiers):
        self.current_mode.key_press(symbol,modifiers)
    def on_key_release(self,symbol,modifiers):
        self.current_mode.key_release(symbol,modifiers)
    def on_mouse_release(self, x, y, button, modifiers):
        self.mouseheld=False
        self.current_mode.mouse_release(x,y,button,modifiers)
    def on_resize(self,width,height):
        super().on_resize(width,height)
        self.current_mode.resize(width,height)
    def on_mouse_press(self,x,y,button,modifiers):
        self.mouseheld=True
        self.current_mode.mouse_press(x,y,button,modifiers)
    def on_mouse_scroll(self,x, y, scroll_x, scroll_y):
        self.current_mode.mouse_scroll(x, y, scroll_x, scroll_y)
    def on_deactivate(self):
        self.minimize()
    def check(self,dt):
        self.sec+=dt
        self.frames+=1
        if self.sec>1:
            self.sec-=1
            self.fpscount.text=str(self.frames)
            self.frames=0

place = windoo(caption='test',fullscreen=True)
place.start()
pyglet.clock.schedule_interval(place.tick,1.0/60)

while True:
    connection.Pump()
    place.nwl.Pump()
    pyglet.clock.tick()
