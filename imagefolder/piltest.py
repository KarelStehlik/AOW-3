from PIL import Image
import os
current="boom biatch/00"

for i in range(10,35,1):
    file = Image.open(current + str(i).zfill(2) + ".png")
#    file=file.rotate(90, expand=True)
    file = file.crop((450, 0, 1550, 1100))  # right top left bottom
    file.thumbnail((256, 256))
    file.save("boom biatch/t" + str(i-10) + ".png")


#for i in range(120):
#    if not i % 3 == 0:
#        os.remove("fire_ring/t" + str(i) + ".png")
#    else:
 #       os.rename("fire_ring/t" + str(i) + ".png", "fire_ring/t" + str(int(i / 3)) + ".png")
