import os
os.environ["IMAGEMAGICK_BINARY"] = r"/opt/homebrew/Cellar/imagemagick/7.0.11-2/bin/convert"
# Import everything needed to edit video clips  
from moviepy.editor import *
import numpy as np
from moviepy import *
from PIL import Image
Image.MAX_IMAGE_PIXELS = 933120000
OutWidth = 1920
OutHeight = 1080

ZZ_currentx1 = 0
ZZ_currenty1 = 0
ZZ_currentx2 = 0
ZZ_currenty2 = 0

def zoom_in_effect(clip, dest, source, duration, duration2):    
    def effect(get_frame, t):
        global OutWidth, OutHeight
        
        # moving smoothly from one coordinate toward another
        ProgressiveCoord = lambda a, b, f: int(a-(a-b)*f) if f<=1.0 else b
        
        # Get the image at time t
        img = Image.fromarray(get_frame(t))
        
        # This factor will trart at 0 and ends at 1
        factor = t/duration

        # Calculate progressive coordinates
        currentx1 = ProgressiveCoord(source[0], dest[0], factor)
        currenty1 = ProgressiveCoord(source[1], dest[1], factor)
        currentx2 = ProgressiveCoord(source[2], dest[2], factor)
        currenty2 = ProgressiveCoord(source[3], dest[3], factor)
        
        # Crop and zoom
        img = img.crop([
            currentx1, currenty1, currentx2, currenty2
        ]).resize((OutWidth,OutHeight), Image.LANCZOS)
        
        # Return and close
        result = np.array(img)
        img.close()
        
        # return modified frame
        return result

    return clip.fl(effect)

def ImageZoomZone(image, x1, y1, x2, y2, duration, duration2, color, keeplasteffect=False, fps=25):
    global OutWidth, OutHeight
    global ZZ_currentx1, ZZ_currenty1, ZZ_currentx2, ZZ_currenty2
    
    cl = ImageClip(image).set_fps(fps).set_duration(duration+duration2).set_position(0,0)
    picwidth, picheight = cl.w, cl.h
 
    # Calculate additional margin to add to picture
    if picwidth>picheight:
        # The picture is horizontal calculate wmargin
        marginw = int(picwidth/2)
        marginh = int(OutHeight/2)
        offx = marginw
        offy = int(marginh/2)
    else:
        # The picture is vertical, calculate hmargin
        marginh = int(picheight/2)
        marginw = int(OutWidth/2)
        offx = int(marginw/2)
        offy = marginh
    
    # Recalculate the input coordinates given the zoom and added margin
    x1 += marginw
    y1 += marginh
    x2 += marginw
    y2 += marginh
    
    # Calculate the y1, y2 to keep aspect ratio
    ym = y1+(y2-y1)/2
    finalheight = (x2 - x1) * OutHeight/OutWidth
    
    # Calculate the final window that respect video aspect ratio
    if y1>int(ym - finalheight/2) and y2<int(ym + finalheight/2):
        # Picture is larger that tall
        # Calculate the y1, y2 to keep aspect ratio
        y1 = int(ym - finalheight/2)
        y2 = int(ym + finalheight/2)
    else:
        # Picture is taller than large
        xm = x1+(x2-x1)/2
        finalwidth = (y2 - y1) * OutWidth/OutHeight
        x1 = int(xm - finalwidth/2)
        x2 = int(xm + finalwidth/2)
    
    # After all these calculation, zone may be outsied of image,
    # if so, we need to add borders and recenter the picture over it
    cocl = ColorClip((picwidth+marginw*2,picheight+marginh*2), color, duration=(duration+duration2))
    cl = CompositeVideoClip([cocl, cl.set_position((marginw, marginh))])
    cocl.close()
    
    # in case we do not need to start over from last zone, reset the starting zone (adding new borders)
    if not keeplasteffect:
        if picwidth>picheight:
            ZZ_currentx1 = offx
            ZZ_currentx2 = offx+picwidth
            ym = offx + picheight/2
            finalheight = picwidth * OutHeight/OutWidth
            ZZ_currenty1 = int(ym - finalheight/2)
            ZZ_currenty2 = int(xm + finalwidth/2)
        else:
            ZZ_currenty1 = offy
            ZZ_currenty2 = offy+picheight
            xm = offx + picwidth/2
            finalwidth = picheight * OutWidth/OutHeight
            ZZ_currentx1 = int(xm - finalwidth/2)
            ZZ_currentx2 = int(xm + finalwidth/2)
        
    # now we have a corrected image and zone, process the effect
    cl = zoom_in_effect(cl, (x1, y1, x2, y2), (ZZ_currentx1, ZZ_currenty1, ZZ_currentx2, ZZ_currenty2), duration, duration2)
    
    # store old coordinates for next animation of the same type (if any)
    ZZ_currentx1 = x1
    ZZ_currenty1 = y1
    ZZ_currentx2 = x2
    ZZ_currenty2 = y2
    return cl
   

# ym=640.0
# x1, y1, x2, y2=(665, 469, 1270, 810)
#cl = ImageZoomZone("/Volumes/Données/Programmation/VideoEdit/LoremIpsum4.png", 665, 618, 1270, 662, 3, (255,255,255))
# xm=1184.0
# x1, y1, x2, y2=(731, 682, 1636, 1191)
#cl = ImageZoomZone("/Volumes/Données/Programmation/VideoEdit/LoremIpsum4.png", 968, 682, 1400, 1191, 3, (255,255,255))
# ym=1248.0
# x1, y1, x2, y2=(534, 1128, 960, 1367)
#cl = ImageZoomZone("/Volumes/Données/Programmation/VideoEdit/LoremIpsum4.png", 534, 1194, 960, 1302, 3, (255,255,255))

# ym=640.0
# x1, y1, x2, y2=(665, 469, 1270, 810)
#cl = ImageZoomZone("/Volumes/Données/Programmation/VideoEdit/LoremIpsum5.png", 146, 82, 753, 121, 3, (255,255,255))
# xm=1184.0
# x1, y1, x2, y2=(731, 682, 1636, 1191)
#cl = ImageZoomZone("/Volumes/Données/Programmation/VideoEdit/LoremIpsum5.png", 450, 140, 882, 651, 3, (255,255,255))
# ym=1248.0
# x1, y1, x2, y2=(534, 1128, 960, 1367)
#cl = ImageZoomZone("/Volumes/Données/Programmation/VideoEdit/LoremIpsum5.png", 14, 649, 447, 762, 3, (255,255,255))

#cl = ImageZoomZone("/Volumes/Données/Programmation/VideoEdit/LoremIpsum6.png", 174, 102, 921, 150, 3, (255,255,255))
#cl = ImageZoomZone("/Volumes/Données/Programmation/VideoEdit/LoremIpsum6.png", 538, 167, 1063, 789, 3, (255,255,255))
#cl = ImageZoomZone("/Volumes/Données/Programmation/VideoEdit/LoremIpsum6.png", 17, 780, 540, 919, 3, (255,255,255))

#cl = ImageZoomZone("/Volumes/Données/Programmation/VideoEdit/LoremIpsum7.png", 170, 80, 901, 149, 3, (255,255,255))
#cl = ImageZoomZone("/Volumes/Données/Programmation/VideoEdit/LoremIpsum7.png", 11, 170, 535, 454, 3, (255,255,255))
#cl = ImageZoomZone("/Volumes/Données/Programmation/VideoEdit/LoremIpsum7.png", 538, 168, 1058, 456, 3, (255,255,255))

#cl1 = ImageZoomZone("/Volumes/Données/Programmation/VideoEdit/LoremIpsum.png", 155, 84, 800, 130, 3, 3, (255,255,255), False)
#cl2 = ImageZoomZone("/Volumes/Données/Programmation/VideoEdit/LoremIpsum.png", 13, 688, 471, 806, 3, 3, (255,255,255), True)
#cl3 = ImageZoomZone("/Volumes/Données/Programmation/VideoEdit/LoremIpsum.png", 475, 147, 935, 687, 3, 3, (255,255,255), True)

#cl = concatenate_videoclips([cl1, cl2, cl3])

#cl.write_videofile("/Volumes/1To/vids.mp4", fps=25, threads=8)
#exit()