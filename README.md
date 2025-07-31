# CommandPad  

Mechanical macropad utilizing the Seeed XIAO RP2040. Has 9 keys plus two rotary encoders, an OLED display, and sk6812 mini-e leds under each key.
CommandPad uses kmk firmware and an optional companion app that allows the OLED display to include information about volume and song titles.

## CAD

There are three 3D printed pieces that fits together using M3 bolts and heatset inserts. The bottom piece holds the pcb, the middle holds the switches, and the top makes it look nice. There is a hole on the back side for a usb plug to utilize CommandPad. The snowboarder sillouette is featured since snowboarding is cool. The case was fully designed in Fusion360. The PCB model was exported from KiCad as a reference.

![Rendering of CommandPad](assets/CommandPad.png)
![Separated pieces of the case](assets/exploded_case.png)

## PCB

The PCB was designed in KiCad.

![Screenshot of the schematic](assets/schematic_screenshot.png)
![Screenshot of the pcb](assets/pcb_screenshot.png)

## Firmware

CommandPad uses KMK to power everything.

- The 3x3 matrix acts as customizable hotkeys currently set to f13 to f21
- The 2 rotary encoders act as a volume control and horizontal scroll wheel
    - Pressing them is by default set to f22 and f23 but it can be change to play/pause, mute, etc.
- The OLED screen stays dark until you change volume or play music with the companion app runnning. Then it will show your volume level or the title of the current song (scrolls if it is too long)

## BOM

9x Cherry MX Switches
9x Blank DSA Keycaps
5x M3x5x4 Heatset inserts
5x M3x16mm SHCS Bolts
9x 1N4148 DO-35 Diodes
2x Through hole resistors 4.7k
9x Through hole capacitor 100nF (.1uF)
9x SK6812 MINI-E LEDs
1x 0.91" 128x32 OLED Display
2x EC11 Rotary Encoder
1x Seeed XIAO RP2040, through hole
1x MCP23017, through hole
1x 74AHCT125, through hole
1x PCB
1x Case (3 printed parts)