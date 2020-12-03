from PodSixNet.Connection import connection,ConnectionListener
from imports import *
from constants import *
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

class mode_intro(mode):
    def __init__(self,win,batch,nwl):
        super().__init__(win,batch)
        nwl.set_mode(self)
    def mouse_drag(self,x, y, dx, dy, button, modifiers):
        self.mouse_move(x,y,dx,dy)
    def tick(self,dt):
        super().tick(dt)
    def network(self,data):
        if "action" in data and data["action"]=="start_game":
            newgame=Game(data["side"])
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
            ("t2f",(0,0,10,0,10,10,0,10))
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
                                        group=pyglet.graphics.OrderedGroup(4),batch=self.batch)
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
    pyglet.clock.tick()
    place.nwl.Pump()
