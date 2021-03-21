# TextualVideoEditor
Video editing without graphical interface, just textual description

# Simple example

'# Initialisation
TargetSize 1920 1080 30

'# Clip de départ
Load V1 "Demofiles/1.MP4"

'# Effect
TextCircleCounter C_Video V1 128 10 ("right","top") 0 10

'# Creating video
Create C_Video "Examples/TextCircleCounter.mp4" 24 libx264
