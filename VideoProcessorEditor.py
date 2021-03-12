############### BEGIN ###############
import os
import subprocess
import glob
from natsort import natsorted
import numpy as np
import math
from gtts import gTTS
import tempfile
from PIL import Image
import cv2
os.environ["IMAGEMAGICK_BINARY"] = r"/opt/homebrew/Cellar/imagemagick/7.0.11-2/bin/convert"

from moviepy.video.tools.drawing import *
from moviepy.editor import *
from moviepy.video.tools import *
from moviepy.video.fx.accel_decel import accel_decel
from moviepy.video.fx.blackwhite import blackwhite
from moviepy.video.fx.blink import blink
from moviepy.video.fx.colorx import colorx
from moviepy.video.fx.crop import crop
from moviepy.video.fx.even_size import even_size
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout
from moviepy.video.fx.freeze import freeze
from moviepy.video.fx.freeze_region import freeze_region
from moviepy.video.fx.gamma_corr import gamma_corr
from moviepy.video.fx.headblur import headblur
from moviepy.video.fx.invert_colors import invert_colors
from moviepy.video.fx.loop import loop
from moviepy.video.fx.lum_contrast import lum_contrast
from moviepy.video.fx.make_loopable import make_loopable
from moviepy.video.fx.margin import margin
from moviepy.video.fx.mask_and import mask_and
from moviepy.video.fx.mask_color import mask_color
from moviepy.video.fx.mask_or import mask_or
from moviepy.video.fx.mirror_x import mirror_x
from moviepy.video.fx.mirror_y import mirror_y
from moviepy.video.fx.painting import painting
from moviepy.video.fx.resize import resize
from moviepy.video.fx.rotate import rotate
from moviepy.video.fx.scroll import scroll
from moviepy.video.fx.speedx import speedx
from moviepy.video.fx.supersample import supersample
from moviepy.video.fx.time_mirror import time_mirror
from moviepy.video.fx.time_symmetrize import time_symmetrize
from moviepy.audio.fx.audio_fadein import audio_fadein
from moviepy.audio.fx.audio_fadeout import audio_fadeout
from moviepy.audio.fx.audio_left_right import audio_left_right
from moviepy.audio.fx.audio_loop import audio_loop
from moviepy.audio.fx.audio_normalize import audio_normalize
from moviepy.audio.fx.volumex import volumex
from moviepy.video.tools.segmenting import findObjects
from skimage.filters import gaussian
from random import randint
import ZoomZone

Image.MAX_IMAGE_PIXELS = 933120000

videopath = "/Volumes/Données/Programmation/VideoEdit/"
ToolPath  = "/Volumes/Données/Programmation/PythonScripts/VideoProcessor/"
OutWidth = 1920
OutHeight = 1080
fontname = "ArialUnicode"
fontsize = 80.
fontcolor = "white"
fontbgcolor = "transparent"
fontstrcolor = "white"
fontstrwidth = 2.
THREADNB = 8
#https://moviepy.readthedocs.io/en/latest/

# helper function
rotMatrix = lambda a: np.array( [[np.cos(a),np.sin(a)], 
                                 [-np.sin(a),np.cos(a)]] )
# WE ANIMATE THE LETTERS
def moveLetters(letters, funcpos):
    return [letter.set_position(funcpos(letter.screenpos,i,len(letters))) for i,letter in enumerate(letters)]

def TextVortex(screenpos,i,nletters):
    d = lambda t : 1.0/(0.3+t**8) #damping
    a = i*np.pi/ nletters # angle of the movement
    v = rotMatrix(a).dot([-1,0])
    if i%2 : v[1] = -v[1]
    return lambda t: screenpos+400*d(t)*rotMatrix(0.5*d(t)*a).dot(v)
    
def TextCascade(screenpos,i,nletters):
    v = np.array([0,-1])
    d = lambda t : 1 if t<0 else abs(np.sinc(t)/(1+t**4))
    return lambda t: screenpos+v*400*d(t-0.15*i)

def TextArrive(screenpos,i,nletters):
    v = np.array([-1,0])
    d = lambda t : max(0, 3-3*t)
    return lambda t: screenpos-400*v*d(t-0.2*i)
    
def TextVortexout(screenpos,i,nletters):
    d = lambda t : max(0,t) #damping
    a = i*np.pi/ nletters # angle of the movement
    v = rotMatrix(a).dot([-1,0])
    if i%2 : v[1] = -v[1]
    return lambda t: screenpos+400*d(t-0.1*i)*rotMatrix(-0.2*d(t)*a).dot(v)

def TxtEffects(lineno, source, text, position, start, eduration, fx):
    global fontname, fontsize, fontcolor, fontbgcolor, fontstrcolor, fontstrwidth
    # Get intermediate data 
    sduration = source.duration
    if start>sduration: start = 0
    if (start+eduration)>sduration: eduration = sduration-start
    clipBefore=None
    if start>0: clipBefore = source.subclip(0,start)
    clipEffect = source.subclip(start, start+eduration)
    clipAfter = None
    if (start+eduration)<sduration: clipAfter = source.subclip(start+eduration, sduration)
    # Create clip
    cl1 = TextClip(DecodeText(text),color=fontcolor, font=fontname, kerning=5, fontsize=fontsize).on_color(col_opacity= 0.5)
    cl1 = cl1.set_position(position)
    cl2 = CompositeVideoClip([cl1], size=(OutWidth,OutHeight))
    # Find objects / letters
    letters = findObjects(cl2,rem_thr=0)
    cl3 = moveLetters(letters,fx)
    if cl3==None or len(cl3)==0: Error(lineno, "TextVortex: no letters can be moved, check letter default color")
    cl4 = CompositeVideoClip(cl3,size=(OutWidth,OutHeight)).subclip(0,eduration)
    cl = CompositeVideoClip([clipEffect, cl4], size=(OutWidth,OutHeight))
    # Merge all together
    clipList=[]
    if clipBefore!=None: clipList.append(clipBefore)
    clipList.append(cl)
    if clipAfter!=None: clipList.append(clipAfter)
    if len(clipList)>1: cl = concatenate_videoclips(clipList)
    return cl

def zoom_in_effect(clip, zoom_ratio=0.04):
    def effect(get_frame, t):
        img = Image.fromarray(get_frame(t))
        base_size = img.size

        new_size = [
            math.ceil(img.size[0] * (1 + (zoom_ratio * t))),
            math.ceil(img.size[1] * (1 + (zoom_ratio * t)))
        ]

        # The new dimensions must be even.
        new_size[0] = new_size[0] + (new_size[0] % 2)
        new_size[1] = new_size[1] + (new_size[1] % 2)

        img = img.resize(new_size, Image.LANCZOS)

        x = math.ceil((new_size[0] - base_size[0]) / 2)
        y = math.ceil((new_size[1] - base_size[1]) / 2)

        img = img.crop([
            x, y, new_size[0] - x, new_size[1] - y
        ]).resize(base_size, Image.LANCZOS)

        result = np.array(img)
        img.close()

        return result

    return clip.fl(effect)

def zoom_out_effect(clip, duration):
    def effect(get_frame, t):
        zoom_ratio = 1/duration
        img = Image.fromarray(get_frame(t))
        base_size = img.size

        new_size = [
            math.ceil(img.size[0] * (2 - (zoom_ratio * t))),
            math.ceil(img.size[1] * (2 - (zoom_ratio * t)))
        ]

        # The new dimensions must be even.
        new_size[0] = new_size[0] + (new_size[0] % 2)
        new_size[1] = new_size[1] + (new_size[1] % 2)

        img = img.resize(new_size, Image.LANCZOS)

        x = math.ceil((new_size[0] - base_size[0]) / 2)
        y = math.ceil((new_size[1] - base_size[1]) / 2)

        img = img.crop([x, y, new_size[0] - x, new_size[1] - y]).resize(base_size, Image.LANCZOS)

        result = np.array(img)
        img.close()
        return result
    return clip.fl(effect)

def ShakeEffect(t, pos):
    speed = 10
    d = randint(0,4)
    if 0 == d:#top
        return (pos[0], pos[1]+speed)
    elif 1 == d:#left
        return (pos[0]-speed, pos[1])
    elif 2 == d:#bot
        return (pos[0], pos[1]-speed)
    else:#right
        return (pos[0]+speed, pos[1])

def GetFFprobePath():
    paths = os.environ['PATH'].split(":")
    for path in paths:
        if os.path.exists(os.path.join(path,"ffprobe")): return os.path.join(path,"ffprobe")
    return ""

# Check if file is quicktime video file (moviepy is not handling very well this format)
def IsVideoQuicktime(pathToInputVideo):
    ffprobe = GetFFprobePath()
    if ffprobe!="":
        cmd = ffprobe + " -export_all True " + pathToInputVideo
        ffprobeOutput = subprocess.check_output(cmd, shell = True,  stderr=subprocess.STDOUT, encoding = 'utf8')
        if "quicktime" in ffprobeOutput: return True
        if ": qt" in ffprobeOutput: return True
    return False

def SplitVideoForEffect(source, start, duration):
    srcduration = source.duration
    before = None
    if start>srcduration:
        DBPrint2("# WARNING: start of effect is after clip's end")
        return source, None, None
    if start>0: before = source.subclip(0, start)
    after = None
    if (start+duration)>srcduration:
        duration = srcduration-start
    else:
        after = source.subclip(start+duration, srcduration)
    effect = source.subclip(start, start+duration)
    return before,effect,after

def JointVideoAfterEffect(before, effect, after):
    clipList=[]
    if before!=None: clipList.append(before)
    if effect!=None: clipList.append(effect)
    if after!=None:  clipList.append(after)
    if len(clipList)>1:
        return concatenate_videoclips(clipList)
    else:
        return clipList[0]

############### ENDFUNCTIONS ###############
import re
import shlex
import sys
from pathlib import Path
import time
import ColorDict

# Internal globals
Debug = False
NeedCode = False
VClips = []
AClips = []
MoviepyCode=""
LastVClipAccessed=""
LastAClipAccessed = ""

def DebugTextEffects(destination, source, text, position, start, eduration, fx):
    DBPrint("source = "+source)
    DBPrint("start = "+start)
    DBPrint("eduration = "+eduration)
    DBPrint("sduration = source.duration")
    DBPrint("if start>sduration: start = 0")
    DBPrint("if (start+eduration)>sduration: eduration = sduration-start")
    DBPrint("clipBefore=None")
    DBPrint("if start>0: clipBefore = source.subclip(0,start)")
    DBPrint("clipEffect = source.subclip(start, start+eduration)")
    DBPrint("clipAfter = None")
    DBPrint("if (start+eduration)<sduration: clipAfter = source.subclip(start+eduration, sduration)")
    DBPrint("cl1 = TextClip("+T(text)+",color=fontcolor, font=fontname, kerning=5, fontsize=fontsize)")
    DBPrint("cl1 = cl1.set_position('"+position+"')")
    DBPrint("cl2 = CompositeVideoClip([cl1], size=(OutWidth,OutHeight))")
    DBPrint("letters = findObjects(cl2,rem_thr=0)")
    DBPrint("cl3 = moveLetters(letters,"+fx+")")
    DBPrint("cl4 = CompositeVideoClip(cl3,size=(OutWidth,OutHeight)).subclip(0,eduration)")
    DBPrint("cl = CompositeVideoClip([clipEffect, cl4], size=(OutWidth,OutHeight))")
    DBPrint("clipList=[]")
    DBPrint("if clipBefore!=None: clipList.append(clipBefore)")
    DBPrint("clipList.append(cl)")
    DBPrint("if clipAfter!=None: clipList.append(clipAfter)")
    DBPrint("if len(clipList)>1: cl = concatenate_videoclips(clipList)")
    DBPrint(destination+" = cl")

# Debug Print
def DBPrint(text):
    global MoviepyCode, Debug, NeedCode
    if Debug:
        print(text)
    if NeedCode:
        MoviepyCode=MoviepyCode+"\n"+text

def DBPrint2(*text):
    global MoviepyCode, Debug, NeedCode
    string = ""
    for a in text:
        if type(a) != type(""):
            string = string + str(a)
        else:
            string = string + a
    if Debug:
        print(string)
    if NeedCode:
        MoviepyCode=MoviepyCode+"\n"+string

def Print(*arg):
    s=""
    for a in arg: s = s + str(a)
    print(s)

def FlushPythonCode():
    global MoviepyCode, NeedCode
    if not NeedCode: return
    header = Path(__file__).read_text()
    h = re.compile(r'\#{15}\sBEGIN\s\#{15}(.*?)\#{15}\sENDFUNCTIONS\s#{15}', flags=re.MULTILINE|re.DOTALL)
    liste = h.findall(header)
    if liste!=None and len(liste)>0:
        MoviepyCode = liste[0]+"\n"+MoviepyCode

def Error(line, text):
    global AClips, VClips
    print(VClips)
    print(AClips)
    if line!=0:
        print("Error at line "+str(line)+": "+text)
    else:
        print("Error: "+str(line)+": "+text)
    exit()

# For debug, convertto string and add ""
def T(value):
    if value==None: return "None"
    value = str(value)
    if len(value)>3 and value[0]=="(" and value[-1]==")" and "," in value:
        valueL = value.replace("(", "").replace(")", "").split(",")
        if len(valueL)==2: 
            return '("'+str(valueL[0])+'", "'+str(valueL[1])+'")'
        elif len(valueL)==3:
            return '('+str(valueL[0])+','+str(valueL[1])+','+str(valueL[2])+')'
        else:
            Error(0, "Position can be in the form of center or (top,left): "+value)
    value = "\\n".join(value.split("\n"))
    return '"'+value+'"'

# For debug display argument of a command
def DisplayArgs(c):
    index = 0
    string=""
    for s in c:
        string = string + str(index)+":"+s+ " "
        index=index+1
    print(string)
    
def CheckMinArgument(liste, sizemin, sizemax, command, line):
    if len(liste)<(sizemin+1): Error(line, command + " takes at least " + str(sizemin) + " argument(s), found "+str(len(liste)-1))
    if len(liste)>(sizemax+1) and sizemax!=0: Error(line, command + " takes less than " + str(sizemax) + " argument(s), found "+str(len(liste)-1))
    return True

# Check the number of arguments of a command and exit if wrong
def CheckArgument(liste, size, command, line):
    if len(liste)!=(size+1): Error(line, command + " takes " + str(size) + " argument(s), found "+str(len(liste)-1))
    return True

def ReadVideoScript(file):
    List = []
    action = []
    lineno = 0
    with open(file, "r") as filestream:
        for line in filestream:
            lineno = lineno+1
            line = line.replace("\n", "")
            # Comment
            if line.startswith('#') or len(line)==0:
                List.append("")
                continue
            # Remove spaces in color notation
            line = re.sub(r'\(\s*(\d+\.*\d*)\s*,\s*(\d+\.*\d*)\s*,\s*(\d+\.*\d*)\s*\)', r'(\1,\2,\3)', line)
            line = re.sub(r'\(\s*(left|center|right)\s*,\s*(top|bottom|center)\s*\)', r'(\1,\2)', line)
            currentline = shlex.split(line)
            #currentline = line.replace("\n", "").split(" ")
            # New instruction
            if not line.startswith('\t'):
                if len(action)>0:
                    List.append(action)
                    action = []
            elif len(action)<=0: Error(lineno, "Syntax error, argument with no related command")
            # add new arguments
            for s in currentline:
                action.append(s)
    # If some action are pending, then add them
    if len(action)>0: List.append(action)
    return List

def SecondsToTimecode(timectr, f):
    m, sf = divmod(timectr, 60)
    h, m  = divmod(m, 60)
    d, h  = divmod(h, 24)
    s = int(sf)
    m = int(m)
    h = int(h)
    return f'{h:02d}:{m:02d}:{s:02d}:{f:02d}'.format(h, m, s, f)

def DecodePosition(string):
    # center
    # (left,bottom)
    if "(" in string:
        listepos = string.replace("(", "").replace(")", "").split(",")
        if len(listepos)!=2: Error(0, "Position can be in the form of center or (top,left)")
        if bool(re.match('^[+-]{0,1}[0-9]+$', listepos[0])) and bool(re.match('^[+-]{0,1}[0-9]+$', listepos[1])):
            return (int(listepos[0]), int(listepos[1]))
        return (listepos[0], listepos[1])
    return '"'+string+'"'

def DecodeText(text):
    return re.sub(r"\\n", "\n", text)#.encode('utf-8')

def DecodeBoolean(text):
    if text=="True" or text=="true" or text=="1": return True
    return False

def DecodeColor(color, RGB=False):
    # If already decoded in RGB, don't do anything
    if type(color) == tuple: return color
    # check if color is in form of (R,G,B)
    if color!=None and "(" in color:
        p = re.compile(r'\((\d+(?:\.){0,1}\d*),(\d+(?:\.){0,1}\d*),(\d+(?:\.){0,1}\d*)\)')
        liste = p.findall(color)
        if liste!=None:
            if ("." in liste[0][0]) or ("." in liste[0][1]) or ("." in liste[0][2]):
                return (float(liste[0][0]),float(liste[0][1]),float(liste[0][2]))
            return (int(liste[0][0]),int(liste[0][1]),int(liste[0][2]))
    # Check if color is None
    if color==None or color=="None" or color=="none": return None
    # Decode color name with equivalent (R,G,B)
    if RGB and color in ColorDict.ColorDict: return ColorDict.ColorDict[color]
    return color

def HHMMSStoS(string):
    p = re.compile(r'(\d+)\:(\d+):(\d+(?:\.\d+){0,1})')
    liste = p.findall(string)
    if liste!=None:
        return int(liste[0][0])*60*60+int(liste[0][1])*60+float(liste[0][2])
    return string

def DecodeTime(timectr, convert=False, clipduration=0):
    if timectr=="clipduration":
        return clipduration
    if not ":" in timectr:
        return float(timectr)
    if convert:
        return HHMMSStoS(timectr)
    return timectr

######   Getting and Storing Video clips #####
def VClipName(name):
    global VClips, LastVClipAccessed
    if name=="Last":
        # Get last clip name used
        if LastVClipAccessed!="":
            return LastVClipAccessed
        Error(0, "No last clip used, script error... (0)")
    # Need to generate name
    if name=="*":
        number = 1
        name = "VideoClip"+str(number)
        try:
            while VClips[name]!=None:
                number += 1
                name = "VideoClip"+str(number)
        except:
            pass
            return name
    return name

def VSetClip(name, value):
    global VClips, LastVClipAccessed
    # Last name used
    name = VClipName(name)
    try:
        VClips[name] = value
        LastVClipAccessed = name
        return name
    except:
        Error(0, "Clip "+name+" do not exist! Correct your script. (1)")
        exit()
    
def VGetClip(name):
    global VClips, LastVClipAccessed
    name = VClipName(name)
    try:
        LastVClipAccessed = name
        return VClips[name]
    except:
        Error(0, "Clip "+name+" do not exist! Correct your script. (2)")

######   Getting and Storing Audio clips #####

def AClipName(name):
    global AClips, LastAClipAccessed
    if name=="Last":
        # Get last clip name used
        if LastAClipAccessed!="":
            return LastAClipAccessed
        Error(0, "No last clip used, script error... (3)")
    # Need to generate name
    if name=="*":
        number = 1
        name = "AudioClip"+str(number)
        try:
            while AClips[name]!=None:
                number += 1
                name = "VideoClip"+str(number)
        except:
            pass
            return name
    return name

def ASetClip(name, value):
    global AClips, LastAClipAccessed
    # Last name used
    name = AClipName(name)
    try:
        AClips[name] = value
        LastAClipAccessed = name
        return name
    except:
        Error(0, "Clip "+name+" do not exist! Correct your script. (4)")
    
def AGetClip(name):
    global AClips, LastAClipAccessed
    name = AClipName(name)
    try:
        LastAClipAccessed = name
        return AClips[name]
    except:
        Error(0, "Clip "+name+" do not exist! Correct your script. (5)")

def VideoClearRotationFlag(file):
    global videopath
    path = os.path.join(videopath, "Temp")
    if not os.path.isdir(path): os.mkdir(path)
    outfile = os.path.join(path, file)
    os.chdir(videopath)
    #subprocess.call(["ffmpeg", '-i', videopath+file, '-c', 'copy', '-metadata:s:v:0', 'rotate=0', outfile], shell=True)
    cmd = 'ffmpeg -i "'+os.path.join(videopath,file)+'" -c copy -metadata:s:v:0 rotate=0 "'+outfile+'"'
    print(cmd)
    subprocess.run([cmd], shell=True)
    return outfile

# Parse and execute commands found in the script
def ParseCommand(commands):
    global videopath, OutWidth, OutHeight, ToolPath, AClips, VClips, THREADNB
    global fontname, fontsize, fontcolor, fontbgcolor, fontstrcolor, fontstrwidth
    global Debug
    fps=0.0
    lineno = 0
    silenceaudio = None
    command=""

    for c in commands:
        lineno = lineno+1
        if Debug==False:
            sys.stdout.write("Running line "+str(lineno))
            sys.stdout.flush()
            sys.stdout.write("\b"*20 )
        if len(c)==0: continue
        
        command = c[0]
        nbarguments = len(c)-1
        fullcommand = ' '.join(c)
        DBPrint("# "+fullcommand)
        if command=="SetPath":
            CheckArgument(c, 1, command, lineno)
            videopath = c[1]
            DBPrint("videopath="+T(videopath))
            #with open(os.path.join(videopath,"ReservedNames.txt"), "w") as text_file:
            #    text_file.write(str(TextClip.list('color')))
            #    text_file.write(str(TextClip.list('font')))
        elif command=="TargetSize":
            # TargetSize width1 height2 fps3
            # TargetSize 480p/SD/720p/HDR/1080p/HD/2160p/UHD/4320p
            CheckMinArgument(c, 1, 3, command, lineno)
            
            if c[1]=="480p":
                OutWidth = 720
                OutHeight = 480
                if nbarguments>1: fps = float(c[2])
            elif c[1]=="SD":
                OutWidth = 1024
                OutHeight = 576
                if nbarguments>1: fps = float(c[2])
            elif c[1]=="720p" or c[1]=="HDR":
                OutWidth = 1280
                OutHeight = 720
                if nbarguments>1: fps = float(c[2])
            elif c[1]=="1080p" or c[1]=="HD":
                OutWidth = 1920
                OutHeight = 1080
                if nbarguments>1: fps = float(c[2])
            elif c[1]=="2160p" or c[1]=="UHD":
                OutWidth = 3840
                OutHeight = 2160
                if nbarguments>1: fps = float(c[2])
            elif c[1]=="4320p":
                OutWidth = 7680
                OutHeight = 4320
                if nbarguments>1: fps = float(c[2])
            else:
                if c[1].isnumeric() and c[2].isnumeric():
                    OutWidth = int(c[1])
                    OutHeight = int(c[2])
                    if nbarguments>2: fps = float(c[3])
                else:
                    Error(lineno, "Unknown resolution, use: 480p/SD/720p/HDR/1080p/HD/2160p/UHD/4320p")
            DBPrint("OutWidth = "+str(OutWidth))
            DBPrint("OutHeight = "+str(OutHeight))
            if fps>0: DBPrint("fps = "+str(fps))
        elif command=="Font":
            #Help("Define font parameters for Text related actions.", "Font fontsize color bgcolor stroke_color stroke_width")
            # Font font1 fontsize2 color3 bgcolor4 stroke_color5 stroke_width6
            CheckArgument(c, 6, command, lineno)
            #if c[4]=="None": c[4] = None
            #if c[5]=="None": c[5] = "white"
            if c[6]=="None": c[6] = "0"
            DBPrint('fontname = '+T(c[1]))
            DBPrint("fontsize = "+c[2])
            DBPrint("fontcolor = "+T(c[3]))
            DBPrint("fontbgcolor = "+T(c[4]))
            DBPrint("fontstrcolor = "+T(c[5]))
            DBPrint("fontstrwidth = "+c[6])
            fontname = c[1]
            fontsize = float(c[2])
            fontcolor = DecodeColor(c[3])
            fontbgcolor = DecodeColor(c[4])
            fontstrcolor = DecodeColor(c[5])
            fontstrwidth = float(c[6])
        elif command=="FinishHere":
            # FinishHere
            return
        elif command=="Thread":
            # Thread number1
            CheckArgument(c, 1, command, lineno)
            THREADNB = c[1]
            DBPrint("THREADNB="+T(THREADNB))
        elif command=="ClearAll":
            # ClearAll
            CheckArgument(c, 0, command, lineno)
            ClearAndCloseAllClips()
        elif command=="Load":
            # Load dest1 filename2 start3 end4
            CheckMinArgument(c, 2, 4, command, lineno)
            destnm = VClipName(c[1])
            file = os.path.join(videopath,DecodeText(c[2]))
            if not os.path.isfile(file): Error(lineno, "File "+file+" does not exist!")
            # BUG quicktile video are out of sync, need to detect and convert first
            #if IsVideoQuicktime(file)
            if nbarguments==2:
                DBPrint2(destnm, " = VideoFileClip(",T(file),").fx(afx.audio_normalize)")
                VSetClip(destnm, VideoFileClip(file).fx(afx.audio_normalize))
            else:
                DBPrint2(destnm," = VideoFileClip("+T(file)+").fx(afx.audio_normalize).subclip(", T(c[3]), ", ",T(c[4]),")")
                VSetClip(destnm, VideoFileClip(file).fx(afx.audio_normalize).subclip(DecodeTime(c[3]), DecodeTime(c[4])))
            fps = max(fps, VGetClip(destnm).fps)
            # BUG si rotation flag dans video remove it
            if VGetClip(destnm).rotation in (90, 270):
                #print("#!!!Rotation of video: "+str(VGetClip(destnm).size))
                VSetClip(destnm, VGetClip(destnm).resize(VGetClip(c[1]).size[::-1]))
                VGetClip(destnm).size=(OutWidth,OutHeight)
                VGetClip(destnm).rotation = 0
                #continue
                #VGetClip(destnm).close()
                #srcfile = VideoClearRotationFlag(c[2])
                #if nbarguments==2:
                #    VSetClip(destnm, VideoFileClip(srcfile).fx(afx.audio_normalize))
                #else:
                #    VSetClip(destnm, VideoFileClip(srcfile).fx(afx.audio_normalize).subclip(DecodeTime(c[3]), DecodeTime(c[4])))
        elif command=="Subtitle":
            # Subtitle dest srtfile
            CheckArgument(c, 2, command, lineno)
            vdestnm = VClipName(c[1])
            file = os.path.join(videopath,c[2])
            if not os.path.isfile(file): Error(lineno, "File "+file+" does not exist!")
            DBPrint2("generator = lambda txt: TextClip(txt, font=fontname, fontsize=fontsize, color=fontcolor, bg_color=fontbgcolor, stroke_color=fontstrcolor, stroke_width=fontstrwidth)")
            DBPrint2("sub = SubtitlesClip(",T(file), ", generator)")
            DBPrint2('sub = sub.set_position(("center", "bottom"))')
            DBPrint2(vdestnm, "= CompositeVideoClip([",vdestnm,", sub])")
            generator = lambda txt: TextClip(txt, font=fontname, fontsize=fontsize, color=fontcolor, bg_color=fontbgcolor, stroke_color=fontstrcolor, stroke_width=fontstrwidth)
            sub = SubtitlesClip(file, generator)
            sub = sub.set_position(("center", "bottom"))
            cl = CompositeVideoClip([VGetClip(vdestnm), sub])
            VSetClip(vdestnm, cl)
        elif command=="BeginAt":
            # BeginAt dest source 00:00:05
            CheckArgument(c, 3, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            DBPrint2(vdestnm," = ",vsrcnm,".subclip(t_start="+T(c[3])+")")
            c[3] = DecodeTime(c[3])
            cl = VGetClip(vsrcnm).subclip(t_start=c[3])
            VSetClip(vdestnm, cl)
        elif command=="EndAt":
            # EndAt dest source 00:00:05
            CheckArgument(c, 3, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            DBPrint(vdestnm+" = "+vsrcnm+".subclip(t_end="+T(c[3])+")")
            c[3] = DecodeTime(c[3])
            cl = VGetClip(vsrcnm).subclip(t_end=c[3])
            VSetClip(vdestnm, cl)
        elif command=="Margin":   # Tested
            # Margin dest1 source2 size3 color4 opacity5
            CheckArgument(c, 5, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            cl = VGetClip(vsrcnm)
            w = cl.w
            h = cl.h
            cl = cl.margin(int(c[3]), color=DecodeColor(c[4]), opacity=float(c[5]))
            VSetClip(vdestnm, cl.resize(newsize=(w,h)))
            DBPrint(vsrcnm+" = "+vsrcnm+".margin("+c[3]+", color="+c[4]+", opacity="+c[5]+")")
            DBPrint(vdestnm+" = "+vsrcnm+".resize(newsize=("+str(w)+","+str(h)+"))")
        elif command=="Scale":
            # Scale dest1 source2 scale3
            CheckArgument(c, 3, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            cl = VGetClip(vsrcnm)
            DBPrint2(vdestnm, vsrcnm, ".resize(",c[3],")")
            VSetClip(vdestnm, cl.resize(float(c[3])))
        elif command=="Position":
            # Position dest1 source2 position3
            CheckArgument(c, 3, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            cl = VGetClip(vsrcnm)
            DBPrint2(vdestnm, vsrcnm,".set_position(",T(c[3]),")")
            VSetClip(vdestnm, cl.set_position(DecodePosition(c[3])))
        elif command=="Crop":
            # Crop dest source x1 x2 y1 y2
            CheckArgument(c, 6, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            DBPrint(vdestnm+"="+vsrcnm+".video.crop(x1="+c[3]+",x2="+c[4]+",y1="+c[5]+',y2='+c[6]+")")
            cl = VGetClip(vsrcnm)
            cl= cl.crop(x1=c[3], y1=c[4], x2=c[5], y2=c[6])
            VSetClip(vdestnm, cl)
        elif command=="ZoomOn":
            # ZoomOn dest source factor start duration position 
            CheckMinArgument(c, 3, 6, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            cl = VGetClip(vsrcnm)
            factor = float(c[3])
            start = 0
            duration = cl.duration
            position = (int(OutWidth/2), int(OutHeight/2))
            if nbarguments>3: start = DecodeTime(c[4])
            if nbarguments>4: duration = DecodeTime(c[5])
            if nbarguments>5: position = DecodePosition(c[6])
            x1 = int(position[0]*factor-OutWidth/2)
            y1 = int(position[1]*factor-OutHeight/2)
            x2 = int(position[0]*factor+OutWidth/2)
            y2 = int(position[1]*factor+OutHeight/2)
            DBPrint2(vdestnm, vsrcnm, ".resize(",factor,")")
            DBPrint2(vdestnm,"=",vsrcnm,".video.crop(x1=",x1,",x2=",y1,",y1=",x2,',y2=',y2,")")
            clipBefore, clipEffect, clipAfter = SplitVideoForEffect(cl, start, duration)
            clipEffect = clipEffect.resize(factor)
            clipEffect = clipEffect.crop(x1=x1, y1=y1, x2=x2, y2=y2)
            VSetClip(vdestnm, JointVideoAfterEffect(clipBefore, clipEffect, clipAfter))
        elif command=="Rotate":
            # Rotate dest source angle
            CheckArgument(c, 3, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            DBPrint(vdestnm+" = vfx.rotate("+vsrcnm+", 90)"+c[3]+")")
            cl = VGetClip(vsrcnm)
            cl = vfx.rotate(cl, 90)
            VSetClip(vdestnm, cl)
        elif command=="Subclip" or command=="Cutout" : # Tested
            # Subclip dest1 source2 strat3 end4
            CheckMinArgument(c, 3, 4, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            cl = VGetClip(vsrcnm)
            start = DecodeTime(c[3])
            if nbarguments==3:
                DBPrint(vdestnm+" = "+vsrcnm+".subclip("+T(c[3])+")")
                cl = cl.subclip(t_start=start)
            else:
                end = DecodeTime(c[4], convert=True)
                if end<0:
                    end = -end
                    DBPrint(vdestnm+" = "+vsrcnm+".subclip("+T([3])+","+vsrcnm+".duration-"+str(end)+")")
                    cl = cl.subclip(start, cl.duration-end)
                else:
                    DBPrint(vdestnm+" = "+vsrcnm+".subclip("+T(c[3])+","+T(c[4])+")")
                    cl = cl.subclip(start, end)
            VSetClip(vdestnm, cl)
        elif command=="Duplicate":
            # Duplicate dest1 source2 start3 end4
            CheckMinArgument(c, 2, 4, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            cl = VGetClip(vsrcnm)
            if nbarguments==2:
                DBPrint(vdestnm+" = "+vsrcnm+".copy()")
                VSetClip(vdestnm, cl.copy())
            else:
                DBPrint(vdestnm+" = "+vsrcnm+".copy().subclip("+c[3]+", "+c[4]+")")
                VSetClip(vdestnm, cl.copy().subclip(float(c[3]), float(c[4])))
####### TEXT RELATED FUNCTIONS ########
        elif command=="Text":
            # Text dest1 source2 Title3 duration4 position5 start6 rotate7
            CheckMinArgument(c, 5, 7, command, lineno)
            destnm = VClipName(c[1])
            srccl = VGetClip(c[2])
            srcnm = VClipName(c[2])
            text = DecodeText(c[3])
            duration = DecodeTime(c[4], clipduration=srccl.duration)
            position = DecodePosition(c[5])
            start = 0 if nbarguments<6 else DecodeTime(c[6])
            rotate = 0 if nbarguments<7 else float(c[7])
            DBPrint2("cl = TextClip(",T(text),",font=",T(fontname),",fontsize=",fontsize,",color=",T(fontcolor),",bg_color=",T(fontbgcolor),",stroke_color=",T(fontstrcolor),",stroke_width=",fontstrwidth,")")
            DBPrint2("cl = cl.set_position(",T(position),").set_duration(",duration,").set_start(",start,")")
            DBPrint2("if ",rotate," != 0: cl = cl.rotate(",rotate,", unit='deg', expand=True)")
            DBPrint2(destnm," = CompositeVideoClip([",srcnm,", cl])")
            cl = TextClip(text, font=fontname, fontsize=fontsize, color=fontcolor, bg_color=fontbgcolor, stroke_color=fontstrcolor, stroke_width=fontstrwidth)
            cl = cl.set_position(position).set_duration(duration).set_start(start)
            if rotate != 0: cl = cl.rotate(rotate, unit='deg', expand=True)
            cl = CompositeVideoClip([srccl, cl])
            VSetClip(destnm, cl)
        elif command=="TextBg":
            # TextBg dest1 source2 Title3 duration4 position5 bgcolor6 start7 rotate8
            CheckMinArgument(c, 6, 8, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            srccl = VGetClip(vsrcnm)
            text = DecodeText(c[3])
            duration = DecodeTime(c[4], clipduration=srccl.duration)
            position = DecodePosition(c[5])
            bgcolor = DecodeColor(c[6], RGB=True)
            start = 0 if nbarguments<7 else DecodeTime(c[7])
            rotate = 0 if nbarguments<8 else float(c[8])
            DBPrint("cl = TextClip("+T(text)+",font="+T(fontname)+",fontsize="+str(fontsize)+",color="+T(fontcolor)+",bg_color="+T(fontbgcolor)+",stroke_color="+T(fontstrcolor)+",stroke_width="+str(fontstrwidth)+")")
            DBPrint("cl = cl.on_color(size=(cl.w+10,cl.h), color="+T(bgcolor)+", pos='center', col_opacity=0.5)")
            DBPrint("cl = cl.set_position("+T(position)+").set_duration("+T(duration)+")).set_start("+T(start)+")")
            DBPrint(vdestnm+" = CompositeVideoClip(["+vsrcnm+", cl], size=(OutWidth,OutHeight))")
            cl = TextClip(DecodeText(c[3]), font=fontname, fontsize=fontsize, color=fontcolor, stroke_color=fontstrcolor, stroke_width=fontstrwidth)
            cl = cl.on_color(size=(cl.w+10,cl.h), color=bgcolor, col_opacity=0.5)
            if rotate != 0: cl = cl.rotate(rotate, unit='deg', expand=True)
            cl = cl.set_position(position).set_duration(duration).set_start(start)
            cl = CompositeVideoClip([srccl, cl])
            VSetClip(vdestnm, cl)
        elif command=="TextBgBottomSlide":
            # TextBgBottomSlide dest1 source2 Title3 duration4 position5 bgcolor6
            CheckArgument(c, 6, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            ypos=0.0
            if c[5]=="bottom": ypos=4*OutHeight/5
            if c[5]=="center": ypos=OutHeight/2
            if c[5]=="top":    ypos=OutHeight/4
            duration=DecodeTime(c[4])
            bgcolor = DecodeColor(c[6], RGB=True)
            DBPrint("ypos = "+str(ypos))
            DBPrint("duration = "+c[4])
            cl = TextClip(DecodeText(c[3]), font=fontname, fontsize=fontsize, color=fontcolor, bg_color=fontbgcolor, stroke_color=fontstrcolor, stroke_width=fontstrwidth)
            DBPrint("cl = TextClip("+T(c[3])+",font="+T(fontname)+",fontsize="+str(fontsize)+",color="+T(fontcolor)+",bg_color="+T(fontbgcolor)+",stroke_color="+T(fontstrcolor)+",stroke_width="+str(fontstrwidth)+")")
            DBPrint("cl = cl.set_position("+c[5]+").set_duration("+c[4]+"))")
            DBPrint("cl = cl.on_color(size=("+str(cl.w+10)+","+str(cl.h)+"), color="+T(bgcolor)+", pos='center', col_opacity=0.5)")
            DBPrint("cl.set_position(lambda t: (max(OutWidth/30,int(OutWidth-0.5*OutWidth*t)), ypos if (t/duration)<(2/3) else ypos+OutHeight*((t/duration)-2/3)*3))")
            DBPrint(c[1]+" = CompositeVideoClip(["+c[2]+", cl], size=(OutWidth,OutHeight)")   
            cl = cl.on_color(size=(cl.w+10,cl.h), color=bgcolor, pos='center', col_opacity=0.5)
            cl = cl.set_position(c[5]).set_duration(float(c[4]))
            cl = cl.set_position(lambda t: (max(OutWidth/30,int(OutWidth-0.5*OutWidth*t)), ypos if (t/duration)<(2/3) else ypos+OutHeight*((t/duration)-2/3)*3))
            cl = CompositeVideoClip([VGetClip(vsrcnm), cl], size=(OutWidth,OutHeight))
            VSetClip(vdestnm, cl)
        elif command=="TextTypewriter":
            # TextTypewriter destination1 source2 texte3 position4 start5 duration6
            CheckArgument(c, 6, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            text = DecodeText(c[3])
            source = VGetClip(vsrcnm)
            position = c[4]
            start = DecodeTime(c[5])
            sound = os.path.join(ToolPath,"Sounds/typewriter.mp3")
            if not os.path.isfile(sound): Error(lineno, "Installation error, file "+sound+" does not exist!")
            eduration = DecodeTime(c[6])
            clipBefore, clipEffect, clipAfter = SplitVideoForEffect(source, start, eduration)
            eduration = clipEffect.duration
            DBPrint('text = '+T(c[3]))
            DBPrint('source = '+vsrcnm)
            DBPrint('position = '+T(position))
            DBPrint('start = '+str(start))
            DBPrint('eduration = '+str(eduration))
            DBPrint('sduration = source.duration')
            DBPrint2("clipBefore, clipEffect, clipAfter = SplitVideoForEffect(",vsrcnm,", ", start,", ",eduration,")")
            DBPrint('FixedTxtDuration = eduration/2')
            DBPrint('MovingTxtDuration = FixedTxtDuration')
            DBPrint("clips_letters = []")
            DBPrint('n = len('+T(text)+')')
            DBPrint('times_start = [MovingTxtDuration*i/(n+1) for i in range(n+2)]')
            DBPrint('times_start[n+1] = times_start[n+1] + FixedTxtDuration')
            DBPrint('message=""')
            DBPrint('i=0')
            DBPrint('for l in text:')
            DBPrint('    i=i+1')
            DBPrint('    message=message+l')
            DBPrint('    clip_text = TextClip(message, color=fontcolor, font=fontname, fontsize=fontsize, kerning=3).set_position(position)')
            DBPrint('    clips_letters.append(clip_text.set_start(times_start[i]).set_end(times_start[i+1]))')
            DBPrint('cl = CompositeVideoClip(clips_letters, size=clip_text.size).set_position(position)')
            DBPrint('clipEffect = CompositeVideoClip([clipEffect, cl], size=(OutWidth,OutHeight))')
            DBPrint('audio_background = AudioFileClip('+T(sound)+')')
            DBPrint('audio_background = audio_background.subclip(t_end=MovingTxtDuration)')
            DBPrint('final_audio = CompositeAudioClip([clipEffect.audio, audio_background])')
            DBPrint('clipEffect = clipEffect.set_audio(final_audio)')
            DBPrint2(vdestnm," = JointVideoAfterEffect(clipBefore, clipEffect, clipAfter))")
            FixedTxtDuration = eduration/2
            MovingTxtDuration = FixedTxtDuration
            #Build typewritter effect
            clips_letters = []
            n = len(text)
            times_start = [MovingTxtDuration*i/(n+1) for i in range(n+2)]
            times_start[n+1] = times_start[n+1] + FixedTxtDuration
            message=""
            i=0
            for l in text:
                i=i+1
                message=message+l
                clip_text = TextClip(message, color=fontcolor, font=fontname, fontsize=fontsize, kerning=3).set_position(position)
                clips_letters.append(clip_text.set_start(times_start[i]).set_end(times_start[i+1]))
            cl = CompositeVideoClip(clips_letters, size=clip_text.size).set_position(position)
            clipEffect = CompositeVideoClip([clipEffect, cl], size=(OutWidth,OutHeight))
            # Add typewritter sound
            audio_background = AudioFileClip(sound)
            audio_background = audio_background.subclip(t_end=MovingTxtDuration)
            final_audio = CompositeAudioClip([clipEffect.audio, audio_background])
            clipEffect = clipEffect.set_audio(final_audio)
            # reconstruct the whole video
            VSetClip(vdestnm, JointVideoAfterEffect(clipBefore, clipEffect, clipAfter))
        elif command=="TextVortex" or command=="TextCascade" or command=="TextArrive" or command=="TextVortexout":
            # TextVortex dest1 source2 text3 position4 start5 duration6
            CheckArgument(c, 6, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            if command=="TextVortex":    fx=TextVortex
            if command=="TextCascade":   fx=TextCascade
            if command=="TextArrive":    fx=TextArrive
            if command=="TextVortexout": fx=TextVortexout
            DebugTextEffects(c[1], c[2], c[3], c[4], c[5], c[6], command)
            VSetClip(vdestnm, TxtEffects(lineno, VGetClip(vsrcnm), c[3], c[4], float(c[5]), float(c[6]), fx))
        elif command == "TextCountDown":
            # TextCountDown dest1 source2 start3 duration4 position5
            CheckArgument(c, 5, command, lineno)
            vdestnm = VClipName(c[1])
            vdestcl = VGetClip(vdestnm)
            vsrcnm = VClipName(c[2])
            vsrccl = VGetClip(vsrcnm)
            start = float(c[3])
            if start == 0: start = vsrccl.duration
            duration = DecodeTime(c[4])
            pos = DecodePosition(c[5])
            fmt = "{:.1f}"
            if float(int(duration))==duration: fmt = "{:.0f}"
            DBPrint2("cliplist = [",vsrcnm,"]")
            cliplist = [vsrccl]
            st = 0
            timectr = start
            while timectr>0 and st<=vsrccl.duration:
                DBPrint2("cl = TextClip(",fmt,".format(",timectr,"),font=fontname, fontsize=fontsize, color=fontcolor, bg_color=fontbgcolor, stroke_color=fontstrcolor, stroke_width=fontstrwidth, align='Center', size=(OutWidth, OutHeight))")
                DBPrint2("cl = cl.set_position(",pos,").set_duration(",duration,").set_start(",st,")")
                DBPrint2("cliplist.append(cl)")
                cl = TextClip(fmt.format(timectr),font=fontname, fontsize=fontsize, color=fontcolor, bg_color=fontbgcolor, stroke_color=fontstrcolor, stroke_width=fontstrwidth, align='Center', size=(OutWidth, OutHeight))
                cl = cl.set_position(pos).set_duration(duration).set_start(st)
                st += duration
                cliplist.append(cl)
                timectr -= duration
            DBPrint2(vdestnm,"=CompositeVideoClip(cliplist)")
            VSetClip(vdestnm, CompositeVideoClip(cliplist))
        elif command == "TextCount":
            # TextCount dest1 source2 start3 end4 duration5 position6
            CheckArgument(c, 6, command, lineno)
            vdestnm = VClipName(c[1])
            vdestcl = VGetClip(vdestnm)
            vsrcnm = VClipName(c[2])
            vsrccl = VGetClip(vsrcnm)
            start = DecodeTime(c[3])
            end = DecodeTime(c[4])
            if end == 0: end = vsrccl.duration
            duration = DecodeTime(c[5])
            pos = DecodePosition(c[6])
            fmt = "{:.1f}"
            if float(int(duration))==duration: fmt = "{:.0f}"
            DBPrint2("cliplist = [",vsrcnm,"]")
            cliplist = [vsrccl]
            st = 0
            timectr = start
            while timectr<=end and st<vsrccl.duration:
                DBPrint2("cl = TextClip(",fmt,".format(",timectr,"),font=fontname, fontsize=fontsize, color=fontcolor, bg_color=fontbgcolor, stroke_color=fontstrcolor, stroke_width=fontstrwidth, align='Center', size=(OutWidth, OutHeight))")
                DBPrint2("cl = cl.set_position(",pos,").set_duration(",duration,").set_start(",st,")")
                DBPrint2("cliplist.append(cl)")
                cl = TextClip(fmt.format(timectr),font=fontname, fontsize=fontsize, color=fontcolor, bg_color=fontbgcolor, stroke_color=fontstrcolor, stroke_width=fontstrwidth, align='Center', size=(OutWidth, OutHeight))
                cl = cl.set_position(pos).set_duration(duration).set_start(st)
                st += duration
                cliplist.append(cl)
                timectr += duration
            DBPrint2(vdestnm,"=CompositeVideoClip(cliplist)")
            VSetClip(vdestnm, CompositeVideoClip(cliplist))
        elif command == "TextTimeCode":
            # TextTimeCode dest1 source2 prefix3 start4 end5 position6
            CheckArgument(c, 6, command, lineno)
            vdestnm = VClipName(c[1])
            vdestcl = VGetClip(vdestnm)
            vsrcnm = VClipName(c[2])
            vsrccl = VGetClip(vsrcnm)
            prefix = DecodeText(c[3])
            start = DecodeTime(c[4])
            end = DecodeTime(c[5])
            if end == 0: end = vsrccl.duration
            duration = 1/vsrccl.fps
            pos = DecodePosition(c[6])
            DBPrint2("cliplist = [",vsrcnm,"]")
            cliplist = [vsrccl]
            st = 0
            frames = 0
            while st<=end and st<vsrccl.duration:
                tstr = prefix + SecondsToTimecode(start+st, frames)
                DBPrint2("cl = TextClip(",tstr,",font=fontname, fontsize=fontsize, color=fontcolor, stroke_color=fontstrcolor, stroke_width=fontstrwidth, align='West')")
                DBPrint2("cl = cl.on_color(size=(cl.w,cl.h),color=",DecodeColor(fontbgcolor, RGB=True),",col_opacity=0.5)")
                DBPrint2("cl = cl.set_position(",pos,").set_duration(",duration,").set_start(",st,")")
                DBPrint2("cliplist.append(cl)")
                cl = TextClip(tstr,font=fontname, fontsize=fontsize, color=fontcolor, stroke_color=fontstrcolor, stroke_width=fontstrwidth, align="West")
                cl = cl.on_color(size=(cl.w,cl.h),color=DecodeColor(fontbgcolor, RGB=True),col_opacity=0.5)
                cl = cl.set_start(st).set_duration(duration).set_position(pos)
                st += duration
                frames = frames+1
                if frames>=vsrccl.fps: frames=0
                cliplist.append(cl)
            DBPrint2(vdestnm,"=CompositeVideoClip(cliplist)")
            VSetClip(vdestnm, CompositeVideoClip(cliplist))
###### PICTURE FUNCTIONS #######
        elif command=="Image":
            # Image dest1 sourcepic2 duration3 scale4 
            CheckArgument(c, 4, command, lineno)
            vdestnm = VClipName(c[1])
            sound = os.path.join(ToolPath,"Silence45M.mp3")
            if not os.path.isfile(sound): Error(lineno, "Installation corrupted, file "+sound+" does not exist!")
            file = os.path.join(videopath,DecodeText(c[2]))
            if not os.path.isfile(file): Error(lineno, "File "+file+" does not exist!")
            DBPrint(vdestnm+" = ImageClip("+sound+").set_duration("+c[3]+").resize("+c[4]+")")
            DBPrint2(vdestnm, ".set_audio(AudioFileClip(",sound,"))")
            cl = ImageClip(file).set_duration(DecodeTime(c[3])).resize(float(c[4]))
            # Add blanck audio to image to avoid an error when creating the file at the end
            if silenceaudio == None: silenceaudio = AudioFileClip(sound)
            cl.set_audio(silenceaudio)
            #cl = CompositeVideoClip([cl])
            VSetClip(c[1], cl)
        elif command=="Logo": # Tested
            # Logo dest1 source2 sourcepic3 duration4 scale5 position6 start7
            CheckMinArgument(c, 6, 7, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            vsrccl = VGetClip(vsrcnm)
            file = os.path.join(videopath,DecodeText(c[3]))
            if not os.path.isfile(file): Error(lineno, "File "+file+" does not exist!")
            duration = DecodeTime(c[4])
            scale = float(c[5])
            position=DecodePosition(c[6])
            start = 0
            if nbarguments == 7: start = DecodeTime(c[7])
            if start < 0: start = vsrccl.duration+start
            if (start+duration)>vsrccl.duration: duration = vsrccl.duration-start
            mask=False
            gif=False
            if ".gif" in file.lower() or ".png" in file.lower(): mask=True
            if ".gif" in file.lower(): gif=True
            if gif:
                DBPrint2("logo = VideoFileClip(",T(file),", has_mask=",mask,").set_duration(",duration,").resize(",scale,").set_position(", T(c[6]),")")
                logo = VideoFileClip(file, has_mask=mask).set_duration(duration).resize(scale).set_position(position)
            else:
                DBPrint2("logo = ImageClip(",T(file),", transparent=", mask,").set_duration(",duration,").resize(",scale,").set_position(",position,")")
                logo = ImageClip(file, transparent=True).set_duration(duration).resize(scale).set_position(position)
            DBPrint2("before, effect, after = SplitVideoForEffect(",vsrcnm,", ", start,", ",duration,")")
            before, effect, after = SplitVideoForEffect(vsrccl, start, duration)
            DBPrint2("effect = CompositeVideoClip([effect, logo])")
            effect = CompositeVideoClip([effect, logo])
            DBPrint2(vdestnm," = JointVideoAfterEffect(before, effect, after))")
            VSetClip(vdestnm, JointVideoAfterEffect(before, effect, after))
        elif command=="ImageSequence": # Tested
            # ImageSequence dest1 sourcepicpattern2 durationeach3
            CheckArgument(c, 3, command, lineno)
            vdestnm = VClipName(c[1])
            file_list = glob.glob(os.path.join(videopath,DecodeText(c[2])))
            file_list_sorted = natsorted(file_list,reverse=False)
            if len(file_list_sorted)<=0: Error(lineno, "No picture match the pattern "+os.path.join(videopath,DecodeText(c[2])))
            DBPrint("file_list_sorted = "+str(file_list_sorted))
            DBPrint("clips = [ImageClip(picname).set_duration("+c[3]+") for picname in file_list_sorted]")
            DBPrint(vdestnm+' = concatenate_videoclips(clips, method="compose"')
            clips = [ImageClip(picname).set_duration(float(c[3])) for picname in file_list_sorted]
            clips = concatenate_videoclips(clips, method="compose")
            VSetClip(vdestnm, clips)
        elif command=="ImageSequenceZoomin": # Tested
            # ImageSequenceZoomin dest1 sourcepicpattern2 durationeach3
            CheckArgument(c, 3, command, lineno)
            vdestnm = VClipName(c[1])
            file_list = glob.glob(os.path.join(videopath,DecodeText(c[2])))
            file_list_sorted = natsorted(file_list,reverse=False)
            if len(file_list_sorted)<=0: Error(lineno, "No picture match the pattern "+os.path.join(videopath,DecodeText(c[2])))
            DBPrint("file_list_sorted = "+str(file_list_sorted))
            DBPrint("slides = []")
            DBPrint("for picname in file_list_sorted:")
            DBPrint("    cl = ImageClip(picname).set_fps(25).set_duration(float("+c[3]+")).resize((OutWidth,OutHeight))))")
            DBPrint("    cl = zoom_in_effect(cl, 0.04)")
            DBPrint("    slides.append(cl)")
            DBPrint(vdestnm+' = concatenate_videoclips(slides, method="compose"')
            slides = []
            for picname in file_list_sorted:
                cl = ImageClip(picname).set_fps(25).set_duration(float(c[3])).resize((OutWidth,OutHeight))
                # Thanks to https://gist.github.com/mowshon/2a0664fab0ae799734594a5e91e518d5
                cl = zoom_in_effect(cl, 0.04)
                slides.append(cl)
            VSetClip(vdestnm, concatenate_videoclips(slides, method="compose"))
        elif command=="ImageSequenceZoomout": # Tested
            # ImageSequenceZoomout dest1 sourcepicpattern2 durationeach3
            CheckArgument(c, 3, command, lineno)
            vdestnm = VClipName(c[1])
            file_list = glob.glob(os.path.join(videopath,DecodeText(c[2])))
            file_list_sorted = natsorted(file_list,reverse=False)
            if len(file_list_sorted)<=0: Error(lineno, "No picture match the pattern "+os.path.join(videopath,DecodeText(c[2])))
            DBPrint("file_list_sorted = "+str(file_list_sorted))
            DBPrint("slides = []")
            DBPrint("for picname in file_list_sorted:")
            DBPrint("    cl = ImageClip(picname).set_fps(25).set_duration(float("+c[3]+")).resize((OutWidth,OutHeight))))")
            DBPrint("    cl = zoom_out_effect(cl, "+c[3]+")")
            DBPrint("    slides.append(cl)")
            DBPrint(vdestnm+' = concatenate_videoclips(slides, method="compose"')
            slides = []
            for picname in file_list_sorted:
                cl = ImageClip(picname).set_fps(25).set_duration(float(c[3])).resize((OutWidth,OutHeight))
                # Thanks to https://gist.github.com/mowshon/2a0664fab0ae799734594a5e91e518d5
                cl = zoom_out_effect(cl, float(c[3]))
                slides.append(cl)
            VSetClip(vdestnm, concatenate_videoclips(slides, method="compose"))
        elif command=="PictureShadingColor":   # Bug and missing color
            # PictureShadingColor dest1 picturefilename2 duration3
            CheckArgument(c, 3, command, lineno)
            vdestnm = VClipName(c[1])
            duration = float(c[3])
            file = os.path.join(videopath,c[2])
            if not os.path.isfile(file): Error(lineno, "File "+file+" does not exist!")
            DBPrint2('duration = ',duration)
            DBPrint2('def f(t, size, a=np.pi / 3, thickness=20):')
            DBPrint2('    w, h = size')
            DBPrint2('    v = thickness * np.array([np.cos(a), np.sin(a)])[::-1]')
            DBPrint2('    center = [int(t * w / duration), h / 2]')
            DBPrint2('    return color_gradient(size, center, v, 0.6, 0.0)')
            DBPrint2('logo = ImageClip(',T(file),', duration=duration).add_mask()')
            DBPrint2('screen = logo.on_color((OutWidth,OutHeight), color=(0, 0, 0), pos="center")')
            DBPrint2('shade = ColorClip((OutWidth,OutHeight), color=(0, 0, 0))')
            DBPrint2('mask_frame = lambda t: f(t, (OutWidth,OutHeight), duration)')
            DBPrint2('shade.mask = VideoClip(ismask=True, make_frame=mask_frame, duration = duration)')
            DBPrint2('VSetClip(',vdestnm,', CompositeVideoClip([logo.set_position(2 * ["center"]), shade], size=(OutWidth,OutHeight)))')
            def f(t, size, duration, a=np.pi / 3, thickness=20):
                w, h = size
                v = thickness * np.array([np.cos(a), np.sin(a)])[::-1]
                center = [int(t * w / duration), h / 2]
                return color_gradient(size, center, v, 0.6, 0.0)
            logo = ImageClip(file, duration=duration).add_mask()
            #screen = logo.on_color((OutWidth,OutHeight), color=(0, 0, 0), pos="center")
            shade = ColorClip((OutWidth,OutHeight), color=(0, 0, 0))
            mask_frame = lambda t: f(t, (OutWidth,OutHeight), duration)
            shade.mask = VideoClip(ismask=True, make_frame=mask_frame, duration = duration)
            VSetClip(vdestnm, CompositeVideoClip([logo.set_position(2 * ["center"]), shade], size=(OutWidth,OutHeight)))
        elif command=="ColorClip":
            # ColorClip dest1 color2 duration3
            CheckArgument(c, 3, command, lineno)
            vdestnm = VClipName(c[1])
            color = DecodeColor(c[2])
            duration = DecodeTime(c[3])
            DBPrint2(vdestnm+" = CompositeVideoClip([ColorClip((OutWidth,OutHeight), "+c[2]+", duration="+c[3]+")])")
            VSetClip(vdestnm, CompositeVideoClip([ColorClip((OutWidth,OutHeight), color, duration=duration)]))
            #VSetClip(c[1], concatenate_videoclips(VGetClip(c[1])))
        elif command=="NoiseClip":
            # NoiseClip dest1 duration2
            CheckArgument(c, 2, command, lineno)
            vdestnm = VClipName(c[1])
            duration = DecodeTime(c[2])
            def make_frame(t): return np.random.random_integers(0, 255, (OutHeight,OutWidth,3))
            clip = VideoClip(make_frame, duration=duration)
            clip = clip.fps=25
            if fps>0: clip = clip.fps=fps
            def blur(image): return gaussian(image.astype(float), sigma=2)
            clip = clip.fl_image( blur )
            DBPrint2("def make_frame(t): return np.random.random_integers(0, 255, (OutHeight,OutWidth,3))")
            DBPrint2(vdestnm," = VideoClip(make_frame, duration=",duration,")")
            DBPrint2(vdestnm," = ", vdestnm, ".fps=",fps)
            DBPrint2("def blur(image): return gaussian(image.astype(float), sigma=2)")
            DBPrint2(vdestnm," = ", vdestnm, ".fl_image( blur )")
            VSetClip(vdestnm, clip)
        elif command=="PictureInPicture":
            # PictureInPicture C_Dest1 C_In2 C_In3 "Titre"4
            CheckArgument(c, 4, command, lineno)
            vdestnm = VClipName(c[1])
            vsrc1nm = VClipName(c[2])
            vsrc2nm = VClipName(c[3])
            DBPrint("picinpic = ("+vsrc2nm)
            DBPrint("    .resize((OutWidth/3, OutHeight/3))")
            DBPrint("    .margin(6, color=(255, 255, 255))")
            DBPrint("    .margin(bottom=20, right=20, opacity=0)")
            DBPrint('    .set_position(("right", "bottom")))')
            DBPrint("txt = TextClip(DecodeText("+T(c[4])+", font=fontname, fontsize=fontsize, color=fontcolor, bg_color=fontbgcolor, stroke_color=fontstrcolor, stroke_width=fontstrwidth)")
            DBPrint("txt = txt.set_duration(source.duration)")
            DBPrint('txt_col = txt.on_color(size=(OutWidth + txt.w+10, txt.h+5),color=(0, 0, 0), pos=(6, "center"), col_opacity=0.6)')
            DBPrint("txt = txt_col.set_position(lambda t: (max(OutWidth / 30, int(OutWidth - 0.5 * OutWidth * t)), max(5 * OutHeight / 6, int(100 * t))))")
            DBPrint(c[1]+" =  CompositeVideoClip([source, txt, picinpic])")
            source = VGetClip(vsrc1nm)
            picinpic = VGetClip(vsrc2nm)
            picinpic = (picinpic
                .resize((OutWidth/3, OutHeight/3))
                .margin(6, color=(255, 255, 255))
                .margin(bottom=20, right=20, opacity=0)
                .set_position(("right", "bottom")))
            txt = TextClip(DecodeText(c[4]), font=fontname, fontsize=fontsize, color=fontcolor, bg_color=fontbgcolor, stroke_color=fontstrcolor, stroke_width=fontstrwidth)
            txt = txt.set_duration(source.duration)
            txt_col = txt.on_color(size=(OutWidth + txt.w+10, txt.h+5),color=(0, 0, 0), pos=(6, "center"), col_opacity=0.6)
            txt = txt_col.set_position(lambda t: (max(OutWidth / 30, int(OutWidth - 0.5 * OutWidth * t)), max(5 * OutHeight / 6, int(100 * t))))
            VSetClip(vdestnm, CompositeVideoClip([source, txt, picinpic]))
############# Audio Functions #########
        elif command=="Volume":
            # Volume dest source volume
            CheckArgument(c, 3, command, lineno)
            DBPrint(c[1]+" = "+c[2]+".volumex("+c[3]+")")
            cl = VGetClip(c[2])
            cl = cl.volumex(float(c[3]))
            VSetClip(c[1], cl)
        elif command=="AudioNormalize":
            # AudioNormalize dest source
            CheckArgument(c, 2, command, lineno)
            adestnm = AClipName(c[1])
            asrcnm = AClipName(c[2])
            DBPrint(adestnm+" = "+asrcnm+".fx(afx.audio_normalize)")
            cl = VGetClip(asrcnm)
            cl = cl.afx(afx.audio_normalize)
            VSetClip(adestnm, cl)
        elif command=="AudioSave":
            # AudioSave destfile source
            CheckArgument(c, 2, command, lineno)
            videoname = VClipName(c[2])
            DBPrint("audio = "+T(videoname)+".audio")
            DBPrint("audio.write_audiofile(os.path.join(videopath,"+T(c[1])+"))")
            cl = AGetClip(videoname)
            audio = cl.audio
            ASetClip(videoname, audio)
            audio.write_audiofile(os.path.join(videopath,DecodeText(c[1])))
        elif command=="AudioLoad":
            # AudioLoad dest1 sourcefile2
            CheckArgument(c, 2, command, lineno)
            dest = AClipName(c[1])
            file = os.path.join(videopath,DecodeText(c[2]))
            if not os.path.isfile(file): Error(lineno, "File "+file+" does not exist!")
            DBPrint2(dest," = AudioFileClip(",T(file),")")
            audio = AudioFileClip(file)
            ASetClip(dest, audio)
        elif command=="VideoSetAudio":
            # VideoSetAudio dest1 audioname2
            CheckArgument(c, 2, command, lineno)
            vdestnm = VClipName(c[1])
            vdestcl = VGetClip(vdestnm)
            asourcenm = AClipName(c[2])
            asourcecl = AGetClip(asourcenm)
            DBPrint(vdestnm+" ="+vdestnm+".set_audio("+asourcenm+")")
            ASetClip(asourcenm, asourcecl) # For updating last audio used
            VSetClip(vdestnm, vdestcl.set_audio(asourcecl))
        elif command=="AudioFromFrequency":
            # AudioFromFrequency dest1 Lfrequency2 Rfrequency3 duration4
            CheckArgument(c, 2, command, lineno)
            adestnm = AClipName(c[1])
            Lfreq = float(c[2])
            Rfreq = float(c[3])
            duration = DecodeTime(c[4])
            DBPrint2("make_frame = lambda t: np.array([np.sin(",Lfreq," * 2 * np.pi * t), np.sin(",Rfreq,' * 2 * np.pi * t)]).T.copy(order="C")')
            DBPrint2(adestnm," = AudioClip(make_frame, duration=",duration,", fps=44100)")
            make_frame = lambda t: np.array([np.sin(Lfreq * 2 * np.pi * t), np.sin(Rfreq * 2 * np.pi * t)]).T.copy(order="C")
            clip = AudioClip(make_frame, duration=duration, fps=44100)
            ASetClip(adestnm, clip)
        elif command=="AudioDelayRepeat":
            # AudioDelayRepeat dest1 source2 delay3 repeat4 decay5
            CheckArgument(c, 5, command, lineno)
            adestnm = AClipName(c[1])
            asourcenm = AClipName(c[2])
            asourcecl = AGetClip(asourcenm)
            delay = DecodeTime(c[3])
            repeat = int(c[4])
            decay = DecodeTime(c[5])
            DBPrint2(adestnm," = ",asourcenm,".fx(audio_delay, offset=",delay,", n_repeats=",repeat,", decayment=",decay,")")
            aclip = asourcecl.fx(audio_delay, offset=delay, n_repeats=repeat, decayment=decay)
            ASetClip(adestnm, aclip)
        elif command=="AudioLoop":
            # AudioLoop dest1 source2 duration3
            CheckArgument(c, 0, command, lineno)
            adestnm = AClipName(c[1])
            asourcenm = AClipName(c[2])
            asourcecl = AGetClip(vsourcenm)
            duration = DecodeTime(c[3])
            DBPrint2(adestnm, " = afx.audio_loop(",asourcenm,", duration=",duration,")")
            audio = afx.audio_loop(asourcecl, duration=duration)
            ASetClip(vdestnm, audio)
        elif command=="Speak":
            # Speak dest1 lang2 Slow3 Text4
            CheckArgument(c, 4, command, lineno)
            adestnm = AClipName(c[1])
            language = c[2]
            slow=DecodeBoolean(c[3])
            text = DecodeText(c[4])
            DBPrint2('speech = gTTS(text = ',T(text),', lang = ',T(language),', slow = ',T(slow),')')
            DBPrint2('f = NamedTemporaryFile(delete=False)')
            DBPrint2('tempfilename = f.name')
            DBPrint2('speech.write_to_fp(f)')
            DBPrint2('f.close()')
            DBPrint2(adestnm, ' = AudioFileClip(tempfilename)')
            speech = gTTS(text = text, lang = language, slow = slow)
            #speech.save("file.mp3")
            f = tempfile.NamedTemporaryFile(delete=False)
            tempfilename = f.name
            speech.write_to_fp(f)
            f.close()
            audio = AudioFileClip(tempfilename)
            ASetClip(adestnm, audio)
        elif command=="AddMusic":
            # AddMusic dest1 source2 sourcefile3 volume4
            CheckArgument(c, 4, command, lineno)
            adestnm = AClipName(c[1])
            asourcenm = AClipName(c[2])
            volume = float(c[4])
            if volume>1 or volume<0: Error(lineno, "Volume must be between 0 and 1")
            source = AGetClip(asourcenm)
            file = os.path.join(videopath,DecodeText(c[3]))
            if not os.path.isfile(file): Error(lineno, "File "+file+" does not exist!")
            DBPrint("source = "+asourcenm)
            DBPrint("source = source.fx(afx.volumex, 1.-"+str(volume)+")")
            DBPrint("audio_background = AudioFileClip("+file+")")
            DBPrint("audio_background = audio_background.fx(afx.audio_normalize)")
            DBPrint("audio_background = audio_background.volumeX("+str(volume)+")")
            source = source.fx(afx.volumex, 1.-volume)
            audio_background = AudioFileClip(file)#, fps=44100)
            duration = source.duration
            DBPrint("duration = "+str(duration))
            if duration<audio_background.duration: DBPrint("audio_background = audio_background.cutout(duration, audio_background.duration)")
            DBPrint("audio_background = afx.audio_loop(audio_background, duration=duration)")
            DBPrint("audio_background = audio_background.cutout(duration, audio_background.duration)")
            DBPrint("final_audio = CompositeAudioClip([source.audio, audio_background])")
            DBPrint(adestnm + " = source.set_audio(final_audio)")
            # Needed if we want to limit the audio duration as defined in parameter
            audio_background = audio_background.fx(afx.audio_normalize)
            audio_background = audio_background.fx(afx.volumex, volume)
            if duration<audio_background.duration: audio_background = audio_background.cutout(duration, audio_background.duration)
            audio_background = afx.audio_loop(audio_background, duration=duration)
            final_audio = CompositeAudioClip([source.audio, audio_background])
            ASetClip(adestnm, source.set_audio(final_audio))
        elif command=="VideoAddSound":
            # VideoAddSound dest1 source2 sourcefile3 volume4 start5
            CheckArgument(c, 5, command, lineno)
            vdestnm = VClipName(c[1])
            vsourcenm = VClipName(c[2])
            vsourcecl = VGetClip(vsourcenm)
            file = os.path.join(videopath,DecodeText(c[3]))
            if not os.path.isfile(file): Error(lineno, "File "+file+" does not exist!")
            volume = float(c[4])
            if volume>1 or volume<0: Error(lineno, "Volume must be between 0 and 1")
            start = DecodeTime(c[5])
            DBPrint2("audio = AudioFileClip(",T(file),")")
            DBPrint2("audio = audio.fx(afx.volumex, ", volume,")")
            audio = AudioFileClip(file)
            audio = audio.fx(afx.volumex, volume)
            duration = audio.duration
            DBPrint2("clipBefore, clipEffect, clipAfter = SplitVideoForEffect(",vsourcenm,", ", start,", ",duration,")")
            clipBefore, clipEffect, clipAfter = SplitVideoForEffect(vsourcecl, start, duration)
            DBPrint2("audio = CompositeAudioClip([clipEffect.audio, audio])")
            audio = CompositeAudioClip([clipEffect.audio, audio])
            DBPrint2("clipEffect = clipEffect.set_audio(audio)")
            clipEffect = clipEffect.set_audio(audio)
            DBPrint2(vdestnm," = JointVideoAfterEffect(clipBefore, clipEffect, clipAfter))")
            VSetClip(vdestnm, JointVideoAfterEffect(clipBefore, clipEffect, clipAfter))
######### Picture Effects ###########
        elif command=="MirrorX":
            # MirrorX dest source
            CheckArgument(c, 2, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            DBPrint(c[1]+"="+vsrcnm+".fx(vfx.mirror_x)")
            cl = VGetClip(vsrcnm)
            cl= cl.fx( vfx.mirror_x)
            VSetClip(vdestnm, cl)
        elif command=="MirrorY":
            # MirrorY dest source
            CheckArgument(c, 2, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            DBPrint(vdestnm+"="+vsrcnm+".fx(vfx.mirror_y)")
            cl = VGetClip(vsrcnm)
            cl= cl.fx( vfx.mirror_y)
            VSetClip(vdestnm, cl)
        elif command=="EffectLumContrast": # Tested
            # EffectLumContrast destination1 source2 lum3(-255-255) contrast4(0-1) thr5(0-255)
            CheckArgument(c, 5, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            DBPrint(vdestnm+" = "+ vsrcnm + ".fx(vfx.lum_contrast, lum="+c[3]+", contrast="+c[4]+", contrast_thr="+c[5]+")")
            VSetClip(vdestnm, VGetClip(vsrcnm).fx(vfx.lum_contrast, lum=float(c[3]), contrast=float(c[4]), contrast_thr=float(c[5])))
        elif command=="EffectPainting": # Tested
            # EffectPainting destination1 source2 saturation3 black4
            CheckArgument(c, 4, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            DBPrint(vdestnm+" = "+vsrcnm + ".fx(vfx.painting, saturation="+c[3]+", black="+c[4]+")")
            VSetClip(vdestnm, VGetClip(vsrcnm).fx(vfx.painting, saturation=float(c[3]), black=float(c[4])))
        elif command=="EffectBW": # Tested
            # EffectBW destination1 source2 color3
            CheckArgument(c, 3, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            c[3] = DecodeColor(c[3])
            if c[3]==None: c[3] = (0,0,0)
            DBPrint(vdestnm+" = "+vsrcnm + ".fx(vfx.blackwhite, RGB="+str(c[3])+")")
            VSetClip(vdestnm, VGetClip(c[2]).fx(vfx.blackwhite, RGB=c[3]))
        elif command=="EffectFadein": # Tested
            # EffectFadein destination1 source2 duration3 color4
            CheckArgument(c, 4, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            duration = DecodeTime(c[3])
            color = DecodeColor(c[4])
            if color==None: color = (0,0,0)
            DBPrint(vdestnm+" = "+vsrcnm + ".fx(vfx.fadein, "+T(duration)+", initial_color="+T(color)+")")
            VSetClip(vdestnm, VGetClip(vsrcnm).fx(vfx.fadein, duration, initial_color=color))
        elif command=="EffectFadeout": # Tested
            # EffectFadeout destination1 source2 source3 duration4 color5
            CheckArgument(c, 4, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            duration = DecodeTime(c[3])
            color = DecodeColor(c[4])
            if color==None: color = (0,0,0)
            DBPrint(vdestnm+" = "+vsrcnm + ".fx(vfx.fadeout, "+T(duration)+", final_color="+T(color)+")")
            VSetClip(vdestnm, VGetClip(vsrcnm).fx(vfx.fadeout, duration, final_color=color))
        elif command=="EffectCrossFadein":
            # EffectCrossFadein dest1 source2 source3 duration4
            CheckArgument(c, 4, command, lineno)
            vdestnm = VClipName(c[1])
            vsrc1nm = VClipName(c[2])
            vsrc2nm = VClipName(c[3])
            DBPrint("clip1a = "+vsrc1nm+".subclip(t_start=0.0,t_end=("+vsrc1nm+".duration-"+c[4]+")")
            DBPrint("clip1b = "+vsrc1nm+".subclip(t_start=("+vsrc1nm+".duration-"+c[4]+"), t_end = "+vsrc1nm+".duration)")
            DBPrint(vsrc2nm+" = "+vsrc2nm+".crossfadein("+c[4]+")")
            DBPrint("clip3 = CompositeVideoClip([clip1b, "+vsrc2nm+"], size=(OutWidth,OutHeight))")
            DBPrint(vdestnm+" = concatenate_videoclips([clip1a, clip3])")
            clip1 = VGetClip(vsrc1nm)
            clip1a = clip1.subclip(t_start=0.0,t_end=(clip1.duration-float(c[4])))
            clip1b = clip1.subclip(t_start=(clip1.duration-float(c[4])), t_end = clip1.duration)
            clip2 = VGetClip(vsrc2nm)
            clip2 = clip2.crossfadein(float(c[4]))
            clip3 = CompositeVideoClip([clip1b, clip2], size=(OutWidth,OutHeight))
            VSetClip(vdestnm, concatenate_videoclips([clip1a, clip3]))
        elif command=="EffectClipFreeze":
            # EffectClipFreeze dest1 source2 Starttime3 duration4
            CheckArgument(c, 4, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm  = VClipName(c[2])
            clip = VGetClip(vsrcnm)
            start  = DecodeTime(c[3])
            duration = DecodeTime(c[4])
            DBPrint2(vdestnm," = ",vsrcnm,".fx(vfx.freeze, t=",start,", freeze_duration=",duration,")")
            clip = clip.fx(vfx.freeze, t=start, freeze_duration=duration)
            VSetClip(vdestnm, clip)
        elif command=="EffectClipInvertColors":
            # EffectClipInvertColors dest1 source2 start3 duration4
            CheckArgument(c, 4, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm  = VClipName(c[2])
            clip = VGetClip(vsrcnm)
            start  = DecodeTime(c[3])
            duration = DecodeTime(c[4])
            DBPrint2("before, effect, after = SplitVideoForEffect(",vsrcnm,", ", start,", ",duration,")")
            before, effect, after = SplitVideoForEffect(clip, start, duration)
            if effect!=None:
                DBPrint2(vdestnm," = ",vsrcnm,".fx(vfx.freeze, t=",start,", freeze_duration=",duration,")")
                effect = effect.fx(vfx.invert_colors)
            DBPrint2(vdestnm," = JointVideoAfterEffect(before, effect, after))")
            VSetClip(vdestnm, JointVideoAfterEffect(before, effect, after))
        elif command=="EffectClipSpeedX":
            # EffectClipSpeedX dest1 source2 factor3 start4 duration5
            CheckArgument(c, 5, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm  = VClipName(c[2])
            clip = VGetClip(vsrcnm)
            factor = float(c[3])
            start  = DecodeTime(c[4])
            duration = DecodeTime(c[5])
            DBPrint2("before, effect, after = SplitVideoForEffect(",vsrcnm,", ", start,", ",duration,")")
            before, effect, after = SplitVideoForEffect(clip, start, duration*factor)
            if effect!=None:
                DBPrint2(vdestnm," = ",vsrcnm,".fx(vfx.speedx, ",factor,")")
                effect = effect.fx(vfx.speedx, factor)
            DBPrint2(vdestnm," = JointVideoAfterEffect(before, effect, after))")
            VSetClip(vdestnm, JointVideoAfterEffect(before, effect, after))
        elif command=="EffectClipRotate":
            # EffectClipRotate dest1 source2 start3 duration4 angle5
            CheckArgument(c, 5, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm  = VClipName(c[2])
            clip = VGetClip(vsrcnm)
            start  = DecodeTime(c[3])
            duration = DecodeTime(c[4])
            angle = float(c[5])
            DBPrint2("before, effect, after = SplitVideoForEffect(",vsrcnm,", ", start,", ",duration,")")
            before, effect, after = SplitVideoForEffect(clip, start, duration)
            if effect!=None:
                DBPrint2(vdestnm," = ",vsrcnm,".fx(vfx.freeze, t=",start,", freeze_duration=",duration,")")
                effect = effect.fx(vfx.rotate, lambda t: angle*t, expand=False).set_duration(duration)
            DBPrint2(vdestnm," = JointVideoAfterEffect(before, effect, after))")
            VSetClip(vdestnm, JointVideoAfterEffect(before, effect, after))
        elif command=="EffectClipRotateScale":
            # EffectClipRotate dest1 source2 bgcolor3
            CheckArgument(c, 3, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm  = VClipName(c[2])
            clip = VGetClip(vsrcnm)
            color = DecodeColor(c[3])
            duration = clip.duration
            angle = 280
            if duration<3.5: Error(lineno, "This effect needs a video clip duration at least of 3s")
            DBPrint2("angle = ", angle)
            DBPrint2("before, effect, after = SplitVideoForEffect(",vsrcnm,", ", duration-3.3,", ",3,")")
            DBPrint2('effect = effect.resize(lambda t: 0.00001+(3-t)/(3)).set_position("center","center")')
            DBPrint2('colclip = ColorClip((OutWidth,OutHeight), ',color,', duration=3)')
            DBPrint2('effect = CompositeVideoClip([colclip,effect])')
            DBPrint2('effect = effect.fx(vfx.rotate, lambda t: angle*t*t, expand=False).set_duration(3)')
            DBPrint2('effect = CompositeVideoClip([colclip,effect])')
            DBPrint2('effect = concatenate_videoclips([effect,colclip.set_duration(0.5)])')
            DBPrint2(vdestnm," = JointVideoAfterEffect(before, effect, None))")
            before, effect, after = SplitVideoForEffect(clip, duration-3.3, 3)
            effect = effect.resize(lambda t: 0.00001+(3-t)/(3)).set_position("center","center")
            colclip = ColorClip((OutWidth,OutHeight), color, duration=effect.duration)
            effect = CompositeVideoClip([colclip,effect])
            effect = effect.fx(vfx.rotate, lambda t: angle*t*t, expand=False).set_duration(3)
            effect = CompositeVideoClip([colclip,effect])
            effect = concatenate_videoclips([effect,colclip.set_duration(0.5)])
            VSetClip(vdestnm, JointVideoAfterEffect(before, effect, None))
        elif command=="EffectCrossFadeout":
            # EffectCrossFadeout dest1 source2 source3 duration4
            CheckArgument(c, 4, command, lineno)
            vdestnm = VClipName(c[1])
            vsrc1nm = VClipName(c[2])
            vsrc2nm = VClipName(c[3])
            DBPrint("clip1a = "+vsrc1nm+".subclip(t_start=0.0,t_end=("+vsrc1nm+".duration-"+c[4]+")")
            DBPrint("clip1b = "+vsrc1nm+".subclip(t_start=("+vsrc1nm+".duration-"+c[4]+"), t_end = "+c[2]+".duration)")
            DBPrint(vsrc2nm+" = "+vsrc2nm+".crossfadein("+c[4]+")")
            DBPrint("clip3 = CompositeVideoClip([clip1b, "+vsrc2nm+"], size=(OutWidth,OutHeight))")
            DBPrint(vdestnm+" = concatenate_videoclips([clip1a, clip3])")
            clip1 = VGetClip(vsrc1nm)
            clip1a = clip1.subclip(t_start=0.0,t_end=(clip1.duration-float(c[4])))
            clip1b = clip1.subclip(t_start=(clip1.duration-float(c[4])), t_end = clip1.duration)
            clip2 = VGetClip(vsrc2nm)
            clip2 = clip2.crossfadeout(float(c[4]))
            clip3 = CompositeVideoClip([clip1b, clip2], size=(OutWidth,OutHeight))
            VSetClip(vdestnm, concatenate_videoclips([clip1a, clip3]))
        elif command=="EffectGammaCorr":
            # EffectGammaCorr dest source value3
            CheckArgument(c, 3, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            DBPrint(vdestnm+"="+vsrcnm+".fx(vfx.mirror_y)")
            cl = VGetClip(vsrcnm)
            cl = vfx.gamma_corr(cl, float(c[3]))
            VSetClip(vdestnm, cl)
        elif command=="EffectColorCorrect":
            # ColorCorrect dest source corlorscale3
            CheckArgument(c, 3, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            colorscale = DecodeColor(c[3])
            def EffectImageRecolor(im, scale=colorscale):
                return im*scale
            DBPrint2("colorscale = ",colorscale)
            DBPrint2("def EffectImageRecolor(im, colorscale=colorscale):")
            DBPrint2("    return im*colorscale")
            DBPrint2(vdestnm,"=",vsrcnm,".fl_image(EffectImageRecolor)")
            cl = VGetClip(vsrcnm)
            cl = cl.fl_image(EffectImageRecolor)#lambda im: im*colorscale)
            VSetClip(vdestnm, cl)
        elif command=="VideoSideBySide":
            # VideoSideBySide dest1 source1 start1 source2 start2 source3 start3 source4 start4
            CheckMinArgument(c, 9, 13, command, lineno)
            if nbarguments != 9 and nbarguments != 13: Error(lineno, "VideoSideBySide only support 4 or 6 video (9, or  13 arguments with their starting times), found "+str(nbarguments))
            if fps<=0: fps=25
            volume=1/6
            if nbarguments == 9: volume=1/4
            vdestnm = VClipName(c[1])
            cl1 = VGetClip(c[2]).volumex(volume)
            cl1n = VClipName(c[2])
            cl1 = cl1.set_start(DecodeTime(c[3]))
            fps=max(fps,cl1.fps)
            cl2 = VGetClip(c[4]).volumex(volume)
            cl2n = VClipName(c[4])
            cl2 = cl2.set_start(DecodeTime(c[5]))
            fps=max(fps,cl2.fps)
            cl3 = VGetClip(c[6]).volumex(volume)
            cl3n = VClipName(c[6])
            cl3 = cl3.set_start(DecodeTime(c[7]))
            fps=max(fps,cl3.fps)
            cl4 = VGetClip(c[8]).volumex(volume)
            cl4n = VClipName(c[8])
            cl4 = cl4.set_start(DecodeTime(c[9]))
            fps=max(fps,cl4.fps)
            if nbarguments == 13:
                cl5 = VGetClip(c[10]).volumex(volume)
                cl5n = VClipName(c[10])
                cl5 = cl5.set_start(DecodeTime(c[11]))
                fps=max(fps,cl1.fps)
                cl6 = VGetClip(c[12]).volumex(volume)
                cl6n = VClipName(c[12])
                cl6 = cl6.set_start(DecodeTime(c[13]))
                fps=max(fps,cl1.fps)
                DBPrint2(vdestnm, " = clips_array([[", cl1n, ", ", cl2n, ", ", cl3n, "], [", cl4n, ", ", cl5n, ", ", cl6n, "]]).fx(afx.audio_normalize)")
                cl =  clips_array([[cl1, cl2, cl3], [cl4, cl5, cl6]])
                cl = cl.set_fps(fps)
                #cl = cl.fx(afx.audio_normalize)
                VSetClip(vdestnm, cl)
            else:
                DBPrint2(vdestnm, " = clips_array([[", cl1n, ", ", cl2n, "], [", cl3n, ", ", cl4n, "]]).fx(afx.audio_normalize)")
                cl = clips_array([[cl1, cl2], [cl3, cl4]])
                cl = CompositeVideoClip([cl])
                cl = cl.set_fps(fps)
                #cl = cl.fx(afx.audio_normalize)
                VSetClip(vdestnm, cl)
        elif command=="EffectThreshold":
            # EffectThreshold dest1 source2 Threshold3
            CheckArgument(c, 3, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            Threshold = int(c[3])
            def EffectImageThreshold(im, Threshold=Threshold):
                th, im_th = cv2.threshold(im, Threshold, 255, cv2.THRESH_BINARY)
                return im_th
            DBPrint2("Threshold = ",Threshold)
            DBPrint2("def EffectImageThreshold(im, Threshold=Threshold):")
            DBPrint2("    th, im_th = cv2.threshold(im, Threshold, 255, cv2.THRESH_BINARY)")
            DBPrint2("    return im_th")
            DBPrint2(vdestnm,"=",vsrcnm,".fl_image(EffectImageThreshold)")
            cl = VGetClip(vsrcnm)
            cl = cl.fl_image(EffectImageThreshold)
            VSetClip(vdestnm, cl)
        elif command=="EffectShake":
            # EffectShake dest1 source2 backgroundpic3 start4 duration5
            CheckArgument(c, 5, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            vsrcncl = VGetClip(vsrcnm)
            backgroundpic = os.path.join(videopath, DecodeText(c[3]))
            if not os.path.isfile(backgroundpic): Error(lineno, "File "+backgroundpic+" does not exist!")
            start = DecodeTime(c[4])
            duration = DecodeTime(c[5])
            DBPrint2("before, effect, after = SplitVideoForEffect(",vsrcnm,", ", start,", ",duration,")")
            before, effect, after = SplitVideoForEffect(vsrcncl, start, duration)
            if effect!=None:
                DBPrint2("back = ImageClip(", T(backgroundpic),").resize(width=effect.size[0])")
                DBPrint2("effect = effect.set_pos(lambda t: ShakeEffect(t, (0,0)))")
                DBPrint2("effect = CompositeVideoClip([back, effect]).set_duration(effect.duration).set_start(",start,")")
                back = ImageClip(backgroundpic).resize(width=effect.size[0])
                effect = effect.set_pos(lambda t: ShakeEffect(t, (0,0)))
                effect = CompositeVideoClip([back, effect]).set_duration(effect.duration).set_start(start)
            DBPrint2(vdestnm," = JointVideoAfterEffect(before, effect, after))")
            VSetClip(vdestnm, JointVideoAfterEffect(before, effect, after))
        elif command=="EffectZoomZone":
            # EffectZoomZone dest1 picture2 x3 y4 x5 y6 duration7 duration8 color9 keep10
            CheckArgument(c, 10, command, lineno)
            vdestnm = VClipName(c[1])
            image = os.path.join(videopath, DecodeText(c[2]))
            if not os.path.isfile(image): Error(lineno, "File "+image+" does not exist!")
            x1 = int(c[3])
            y1 = int(c[4])
            x2 = int(c[5])
            y2 = int(c[6])
            duration1 = int(c[7])
            duration2 = int(c[8])
            color = DecodeColor(c[9])
            keep = DecodeBoolean(c[10])
            DBPrint2(vdestnm, " = ZoomZone.ImageZoomZone(",image,", ",x1,", y1, ",x2,", y2, ", duration1,", ",duration2,", ",color,", ",keep,", ",fps,")")
            VSetClip(vdestnm, ZoomZone.ImageZoomZone(image, x1, y1, x2, y2, duration1, duration2, color, keep, fps))
        elif command=="ReducingCircle":
            # ReducingCircle dest1 source2 text3 start4 duration5
            CheckArgument(c, 5, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            vsrccl = VGetClip(vsrcnm)
            start = DecodeTime(c[4])
            text = DecodeText(c[3])
            duration = DecodeTime(c[5], convert=True)
            DBPrint2("ClipBefore, ClipEffect, ClipAfter = SplitVideoForEffect(",vsrcnm,", ", start,", ",duration,")")
            DBPrint2('ClipEffect = ClipEffect.add_mask()')
            DBPrint2('ClipEffect.mask.get_frame = lambda t: circle(screensize=(OutWidth,OutHeight), center=(OutWidth/2,OutHeight/4), radius=max(0,int(800-200*t)), col1=1, col2=0, blur=4)')
            DBPrint2('cl = TextClip(',T(c[3]),', font=fontname, color=fontcolor, fontsize=fontsize).set_duration(duration)')
            DBPrint2('ClipEffect = CompositeVideoClip([cl.set_position("center"), ClipEffect], size=(OutWidth,OutHeight))')
            DBPrint2(vdestnm," = JointVideoAfterEffect(ClipBefore, ClipEffect, ClipAfter))")
            if duration<5: Error(lineno, "Effect duration can't be lower than 5s.")
            ClipBefore, ClipEffect, ClipAfter = SplitVideoForEffect(vsrccl, start, duration)
            ClipEffect = ClipEffect.add_mask()
            ClipEffect.mask.get_frame = lambda t: circle(screensize=(OutWidth,OutHeight), center=(OutWidth/2,OutHeight/4), radius=max(0,int(800-200*t)), col1=1, col2=0, blur=4)
            cl = TextClip(text, font=fontname, color=fontcolor, fontsize=fontsize).set_duration(ClipEffect.duration)
            ClipEffect = CompositeVideoClip([cl.set_position('center'), ClipEffect], size=(OutWidth,OutHeight))
            VSetClip(vdestnm, JointVideoAfterEffect(ClipBefore, ClipEffect, ClipAfter))
######## Video creation ########
        elif command=="Merge": #Tested
            #Merge destination source1 source2...
            CheckMinArgument(c, 3, 0, command, lineno)
            vdestnm = VClipName(c[1])
            DBPrint("l=[]")
            l = []
            for i in range(2, nbarguments+1):
                vsrcnm = VClipName(c[i])
                DBPrint("l.append("+vsrcnm+")")
                cl = VGetClip(vsrcnm)
                l.append(cl)
            DBPrint(vdestnm+" = concatenate_videoclips(l)")
            VSetClip(vdestnm, concatenate_videoclips(l))
        elif command=="MergeAll": #Tested
            #MergeAll destination
            CheckArgument(c, 1, command, lineno)
            vdestnm = VClipName(c[1])
            DBPrint("l=[]")
            l = []
            for video in VClips:
                DBPrint("l.append("+video+")")
                cl = VGetClip(video)
                l.append(cl)
            DBPrint(vdestnm+" = concatenate_videoclips(l)")
            VSetClip(vdestnm, concatenate_videoclips(l))
        elif command=="AllTogether":
            # AllTogether dest1 source2 text3 source3 text4...
            CheckMinArgument(c, 4, 0, command, lineno)
            vdestnm = VClipName(c[1])
            vsrcnm = VClipName(c[2])
            cl = VGetClip(vsrcnm)
            nbvideo = (nbarguments-1)/2
            for side in range(1, 7):
                if (side*side)>=nbvideo: break
            DBPrint("side="+str(side))
            DBPrint("liste = []")
            liste = []
            i=2
            while i<=nbarguments:
                cl = VGetClip(c[i])
                text = DecodeText(c[i+1])
                if text!="":
                    DBPrint('txt = TextClip('+T(text)+', font=fontname, fontsize=fontsize, color=fontcolor, stroke_color=fontstrcolor, stroke_width=fontstrwidth, bg_color=fontbgcolor, align="center")')
                    DBPrint('txt = txt.set_position(("center", "bottom"))')
                    DBPrint("cl = CompositeVideoClip([cl, txt]).set_duration(cl.duration)")
                    txt = TextClip(text, font=fontname, fontsize=fontsize, color=fontcolor, stroke_color=fontstrcolor, stroke_width=fontstrwidth, bg_color=fontbgcolor, align="center")
                    txt = txt.set_position(("center", "bottom")).set_duration(cl.duration)
                    cl = CompositeVideoClip([cl, txt])
                    #cl = cl.resize(int(OutWidth/side),int(OutHeight/side))
                else:
                    DBPrint("cl = cl.resize(width="+str(int(OutWidth/side))+",height="+str(int(OutHeight/side))+")")
                    cl = cl.resize(width=int(OutWidth/side),height=int(OutHeight/side))
                DBPrint("liste.append(cl)")
                liste.append(cl)
                i=i+2
            DBPrint("for i in range(nbarguments-3, side*side+1):liste.append(ColorClip((int(OutWidth/side),int(OutHeight/side)), (0,0,0), duration=0.1))")
            for i in range(nbarguments-3, side*side+1): liste.append(ColorClip((int(OutWidth/side),int(OutHeight/side)), (0,0,0), duration=0.1))
    
            DBPrint("array = []")
            DBPrint("subl = []")
            DBPrint("section=0")
            DBPrint("for el in liste:")
            DBPrint("    if section==0: subl = []")
            DBPrint("    subl.append(el)")
            DBPrint("    section = section+1")
            DBPrint("    if section>=side: section=0")
            DBPrint("    if section==0:")
            DBPrint("        array.append(subl)")
            DBPrint("        subl=None")
            DBPrint("if subl!=None: array.append(subl)")
            DBPrint(vdestnm+" = clips_array(array)")
            array = []
            subl = []
            section=0
            for el in liste:
                if section==0: subl = []
                subl.append(el)
                section = section+1
                if section>=side: section=0
                if section==0:
                    array.append(subl)
                    subl=None
            if subl!=None: array.append(subl)
            VSetClip(vdestnm, clips_array(array))
        elif command=="Create":
            # Create source1 file2 fps3 codec4
            CheckMinArgument(c, 2, 4, command, lineno)
            vsrcnm = VClipName(c[1])
            cl = VGetClip(vsrcnm)
            file = os.path.join(videopath,c[2])
            codec = "libx264"
            bitrate = "10000K"
            if fps==0: fps=25
            audiocodec = 'aac'
            if nbarguments>2: fps = float(c[3])
            if nbarguments>3: codec = DecodeText(c[4])
            if nbarguments>4: audiocodec = DecodeText(c[5])
            DBPrint(vsrcnm+" = "+c[1]+".resize(newsize=(OutWidth,OutHeight))")
            DBPrint(vsrcnm+".write_videofile("+T(file)+", fps=" + str(fps) +", codec="+T(codec)+", bitrate="+T(bitrate)+", audio_codec="+T(audiocodec)+", threads="+T(THREADNB)+")")
            cl = cl.resize(newsize=(OutWidth,OutHeight))
            cl.write_videofile(file, fps=fps, codec=codec, bitrate=bitrate, audio_codec=audiocodec,threads=THREADNB)
            open(file)
        # Template for new effects
        elif command=="":
            # Template dest1 source2 file3
            CheckArgument(c, 0, command, lineno)
            #CheckMinArgument(c, 3, 6, command, lineno)
            vdestnm = VClipName(c[1])
            vdestcl = VGetClip(vdestnm)
            vsourcenm = VClipName(c[2])
            vsourcecl = VGetClip(vsourcenm)
            file = os.path.join(videopath,c[3])
            if not os.path.isfile(file): Error(lineno, "File "+file+" does not exist!")
            #if nbarguments>3:
            DBPrint2("clipBefore, clipEffect, clipAfter = SplitVideoForEffect(",source,", ",start,", ", duration,")")
            clipBefore, clipEffect, clipAfter = SplitVideoForEffect(source, start, eduration)
            DBPrint2(vdestnm," = JointVideoAfterEffect(before, effect, after))")
            VSetClip(vdestnm, JointVideoAfterEffect(before, effect, after))
            #VSetClip(vdestnm, vsourcecl)

def BuildDemo():
    global videopath
    file_list = glob.glob(os.path.join(videopath,"Examples/*.txt"))
    for file in file_list: runFile(file)

def ClearAndCloseAllClips():
    global VClips, AClips, LastVClipAccessed, LastAClipAccessed
    try:
        for video in VClips:
            video.close()
        for audio in AClips:
            audio.close()
    except:
        pass
    VClips = dict()
    AClips = dict()
    LastVClipAccessed=""
    LastAClipAccessed=""
    
def runFile(file):
    global MoviepyCode, VClips, AClips, videopath, OutWidth, OutHeight, LastVClipAccessed, LastAClipAccessed
    print("Execution of "+file)
    VClips = dict()
    AClips = dict()
    MoviepyCode=""
    OutWidth = 1920
    OutHeight = 1080
    l = ReadVideoScript(file)
    ParseCommand(l)
    if NeedCode:
        FlushPythonCode()
        with open(os.path.join(videopath,"Output.py"), "w") as text_file:
            text_file.write(MoviepyCode)
    ClearAndCloseAllClips()

def main():
    global NeedCode, Debug, videopath, ToolPath
    NeedCode=False
    Debug=False
    start_time = time.time()
    runFile(videopath+"VideoScript.txt")
    #BuildDemo()
    print("DONE IN %s seconds" % (time.time() - start_time))
    
if __name__ =='__main__':
    main()
    exit()
