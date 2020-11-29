from PodSixNet.Connection import connection,ConnectionListener
from imports import *
from constants import *
connection.DoConnect(('192.168.1.132', 5071))
class MyNetworkListener(ConnectionListener):
    def __init__(self,*args,**kwargs):
        super().__init__()
        self.start=False
        self.mode=None
    def set_mode(self,m):
        self.mode=m
    def Network(self,data):
        melf.mode.network(data)

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

class windoo(pyglet.window.Window):
    def start(self):
        self.nwl=MyNetworkListener()
        self.batch = pyglet.graphics.Batch()
        self.sec=self.frames=0
        self.fpscount=pyglet.text.Label(x=5,y=5,text="0",color=(255,255,255,255),
                                        group=pyglet.graphics.OrderedGroup(4),batch=self.batch)
        self.mouseheld=False
        self.current_mode=mode(self,self.batch,self.nwl)
        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)
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
        self.nwl.pump()
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
    try:
        connection.Pump()
        pyglet.clock.tick()
    except Exception as a:
        place.on_close()
        place.dispatch_events()
        raise(a)
