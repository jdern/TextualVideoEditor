import gizeh
from moviepy.editor import *
import numpy as np

def gizeh_pie(r, a1, a2, xy, **kw):
    def draw(ctx):
        ctx.move_to(xy[0],xy[1])
        ctx.arc(xy[0], xy[1], r, a1, a2)
        ctx.close_path()
    return gizeh.shape_element(draw, **kw)

def make_frame_countdownup(t, size, value, mask, duration, font=1/3):
    surface = gizeh.Surface(size,size)#, bg_color=(255,255,255))
    R1 = int(size/2)
    R2 = int(size*font)
    pieobj = gizeh_pie(R1, 0, 2*np.pi*t/duration, (size/2,size/2), fill=(255,255,255))
    pieobj.draw(surface)
    circle = gizeh.circle(R2, xy = (size/2,size/2), fill=(255,0,0))
    circle.draw(surface)
    text = str(int(t))
    if value>0: text = str(value-int(t)-1)
    text = gizeh.text(text, fontfamily="Arial",  fontsize=R2, fill=(0,0,0), xy=(size/2,size/2), angle=0)
    text.draw(surface)
    img = surface.get_npimage(transparent=mask)
    if mask: img = img[:,:,0]/255.0
    return img

def AddCircleCounter(videoclip, size, duration, position, startvalue):
    clip_mask = VideoClip(lambda t: make_frame_countdownup(t, size, startvalue, True, duration), ismask=True)
    clip = VideoClip(lambda t: make_frame_countdownup(t, size, startvalue, False, duration), duration=duration).set_mask(clip_mask)
    final_clip = CompositeVideoClip([videoclip,clip.set_position(position)])
    return final_clip
