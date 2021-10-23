from PIL import Image
import os

current = "explosion2/tt"
# '''
for i in range(2, 106, 1):
    file = Image.open(current + str(i).zfill(4) + ".png")
    #file = file.rotate(90, expand=True)
    file = file.crop((300, 110, 600, 390))  # right top left bottom
    # file.thumbnail((256, 256))
    file.save("explosion2/t" + str(i-2) + ".png")

'''
bg=Image.open("faura.png")
bg=bg.resize((960,960))
for i in range(151):
    meteor=Image.open(current + str(i) + ".png")
    new=Image.new('RGBA', (960,1360), (250, 250, 250,0))
    new.paste(bg,(0,0))
    new.paste(meteor, (334, 400), meteor)
    new.save("fireball/tt" + str(i) + ".png")
'''

# for i in range(120):
#    if not i % 3 == 0:
#        os.remove("fire_ring/t" + str(i) + ".png")
#    else:
#       os.rename("fire_ring/t" + str(i) + ".png", "fire_ring/t" + str(int(i / 3)) + ".png")
