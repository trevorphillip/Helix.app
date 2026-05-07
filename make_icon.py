from PIL import Image, ImageDraw
import os, math
os.makedirs("helix_desktop", exist_ok=True)

base = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
d = ImageDraw.Draw(base)
d.ellipse((16,16,240,240), fill=(20,30,60,255))
for t in range(0, 256, 12):
    x1 = 80 + int(30 * math.sin(t/18))
    x2 = 176 + int(30 * math.cos(t/18))
    d.line((x1, t, x2, t), fill=(120,200,255,255), width=3)
d.arc((46,16,210,240), start=0, end=360, fill=(160,230,255,180), width=3)

# write multi-size .ico
base.save("helix_desktop/helix.ico", sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])
print("Wrote helix_desktop/helix.ico")
