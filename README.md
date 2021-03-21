# TextualVideoEditor
Video editing without graphical interface, just textual description

# Simple example

\# Initialisation, final video will be 1920x1080

TargetSize 1920 1080

\# Load a first clip from demo files and name it V1

Load V1 "Demofiles/1.MP4"

\# Effect apply on V1 a time counting effect (size 128p). Time will be on right top, starting at time 0 and ending a time = 10s of V1, the result is named C_Video

TextCircleCounter C_Video V1 128 ("right","top") 0 10

\# Creating the final video from C_Video and save it in mp4 format in 30fps

Create C_Video "Examples/TextCircleCounter.mp4" 30 libx264
