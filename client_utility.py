import pyglet
from pyglet.gl import *
import images
import groups
from constants import *
class TextureEnableGroup(pyglet.graphics.OrderedGroup):
    def set_state(self):
        glEnable(GL_TEXTURE_2D)
    def unset_state(self):
        glDisable(GL_TEXTURE_2D)

texture_enable_groups = [TextureEnableGroup(i) for i in range(10)]

class TextureBindGroup(pyglet.graphics.Group):
    def __init__(self, texture, layer=0):
        super(TextureBindGroup, self).__init__(parent=texture_enable_groups[layer])
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
