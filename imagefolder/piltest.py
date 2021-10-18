from PIL import Image
import os
current="explosion/aaa"

for i in range(120,121,2):
    file = Image.open(current + str(i).zfill(4) + ".png")
#    file=file.rotate(90, expand=True)
    file = file.crop((650, 250, 1250, 850))  # right top left bottom
    file.thumbnail((256, 256))
    file.save("explosion/tt" + str(int(i/2)) + ".png")


#for i in range(120):
#    if not i % 3 == 0:
#        os.remove("fire_ring/t" + str(i) + ".png")
#    else:
 #       os.rename("fire_ring/t" + str(i) + ".png", "fire_ring/t" + str(int(i / 3)) + ".png")
