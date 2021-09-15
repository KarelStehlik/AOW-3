from PIL import Image
import os
current="fire_ring/t"

for i in range(40):
    file = Image.open(current + str(i) + ".png")
#    file=file.rotate(90, expand=True)
    file = file.crop((445, 30, 1480, 1050))  # right top left bottom
    file.thumbnail((256, 256))
    file.save("test/t" + str(i) + ".png")


#for i in range(120):
#    if not i % 3 == 0:
#        os.remove("fire_ring/t" + str(i) + ".png")
#    else:
 #       os.rename("fire_ring/t" + str(i) + ".png", "fire_ring/t" + str(int(i / 3)) + ".png")
