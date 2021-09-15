from PIL import Image
import os

#for i in range(130):
#    file = Image.open("test/t" + str(i) + ".png")
#    file2=file.rotate(90, expand=True)
#    file2.thumbnail((256, 256))
#    file2 = file2.crop((35, 190, 115, 250))  # right top left bottom
#    file2.save("flame_wave/t" + str(i) + ".png")
for i in range(130):
    if not i%4==0:
        os.remove("flame_wave/t" + str(i) + ".png")
    else:
        os.rename("flame_wave/t" + str(i) + ".png", "test/t" + str(int(i/4)) + ".png")


