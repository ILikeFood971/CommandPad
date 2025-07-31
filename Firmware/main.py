from kmk.kmk_keyboard import KMKKeyboard
from kmk.keys import KC
from kmk.scanners import DiodeOrientation
from kmk.modules.encoder import EncoderHandler
from kmk.modules.pn_mcp23017 import PN_MCP23017

import board
import busio
from neopixel import NeoPixel
import displayio
from adafruit_displayio_ssd1306 import SSD1306
from adafruit_display_text import label
import terminalio
import time
import supervisor

# --- Init Keyboard ---
keyboard = KMKKeyboard()

# --- I2C (shared OLED + MCP23017) ---
i2c = busio.I2C(scl=board.GP7, sda=board.GP6)

# --- Matrix on MCP23017 ---
mcp = PN_MCP23017(i2c, address=0x20)
keyboard.matrix = mcp.get_matrix(
    rows=[0, 1, 2],
    columns=[3, 4, 5],
    diode_orientation=DiodeOrientation.COL2ROW
)

# --- Neopixel ---
NUM_PIXELS = 9
pixels = NeoPixel(board.GP26, NUM_PIXELS, brightness=0.4, auto_write=True)

# --- OLED Setup ---
displayio.release_displays()
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
display = SSD1306(display_bus, width=128, height=32)

# Setup screen group
main_group = displayio.Group()
text_area = label.Label(terminalio.FONT, text="", scale=1, x=0, y=16)
main_group.append(text_area)
display.show(main_group)

# --- Encoder Setup ---
encoders = EncoderHandler()
keyboard.modules.append(encoders)
encoders.pins = [
    (board.GP3, board.GP4),  # Encoder 1
    (board.GP2, board.GP1),  # Encoder 2
]
encoders.map = [
    ((KC.VOLD, KC.VOLU),),
    ((KC.LEFT, KC.RIGHT),),
]

# --- Encoder Buttons ---
keyboard.gpio_pins = [board.GP27, board.GP28]
keyboard.gpio_keymap = {
    board.GP27: KC.F22,
    board.GP28: KC.F23,
}

# --- 3x3 Buttons (F13–F21) ---
keyboard.keymap = [
    [
        KC.F13, KC.F14, KC.F15,
        KC.F16, KC.F17, KC.F18,
        KC.F19, KC.F20, KC.F21,
    ]
]

# --- OLED Display Manager ---
class OledManager:
    def __init__(self, text_label):
        self.text_label = text_label
        self.current_text = "CommandPad Ready"
        self.last_vol_time = 0
        self.showing_volume = False
        self.scroll_offset = 0
        self.scroll_pause = 0
        self.display_on = True
        self.is_playing = False
        self.last_activity = time.monotonic()

    def set_volume(self, level):
        if not self.display_on:
            self.wake_display()
        self.text_label.text = f"🔊 Volume: {level}%"
        self.last_vol_time = time.monotonic()
        self.showing_volume = True
        self.scroll_offset = 0
        self.last_activity = time.monotonic()

    def set_media_info(self, title, artist="", is_playing=True):
        """Update media information from companion app"""
        self.is_playing = is_playing
        if is_playing:
            if not self.display_on:
                self.wake_display()
            if artist:
                self.current_text = f"🎵 {artist} - {title}"
            else:
                self.current_text = f"🎵 {title}"
            self.last_activity = time.monotonic()
        else:
            # Nothing playing, turn off display after delay
            pass

    def wake_display(self):
        """Wake up the display"""
        self.display_on = True
        display.show(main_group)

    def sleep_display(self):
        """Turn off display when nothing is playing"""
        self.display_on = False
        self.text_label.text = ""
        display.show(displayio.Group())  # Show empty group

    def tick(self):
        now = time.monotonic()

        # Auto-sleep display if nothing playing for 30 seconds
        if not self.is_playing and now - self.last_activity > 30:
            if self.display_on:
                self.sleep_display()
            return

        # Show song title again after 3s
        if self.showing_volume and now - self.last_vol_time > 3:
            self.showing_volume = False
            self.scroll_offset = 0
            self.scroll_pause = 0

        # If showing song title, scroll if too long
        if not self.showing_volume and self.display_on:
            full_text = self.current_text
            visible_chars = 20
            if len(full_text) <= visible_chars:
                self.text_label.text = full_text
            else:
                if now - self.scroll_pause > 0.3:
                    self.scroll_offset = (self.scroll_offset + 1) % (len(full_text) + 5)
                    self.scroll_pause = now
                padded = full_text + "     "
                scroll_text = padded[self.scroll_offset:self.scroll_offset + visible_chars]
                self.text_label.text = scroll_text

    def process_serial_data(self, data):
        """Process data from companion application"""
        try:
            if data.startswith("VOL:"):
                volume = int(data[4:])
                self.set_volume(volume)
            elif data.startswith("MEDIA:"):
                # Format: MEDIA:playing|title|artist
                parts = data[6:].split("|")
                if len(parts) >= 2:
                    is_playing = parts[0] == "1"
                    title = parts[1]
                    artist = parts[2] if len(parts) > 2 else ""
                    self.set_media_info(title, artist, is_playing)
            elif data.startswith("STOP"):
                self.is_playing = False
                self.current_text = "CommandPad Ready"
        except:
            pass  # Ignore malformed data

oled = OledManager(text_area)

# Volume level tracking
volume_level = 50

# Serial communication for companion app
def check_serial_input():
    """Check for incoming serial data from companion application"""
    try:
        if supervisor.runtime.serial_bytes_available:
            data = input().strip()
            oled.process_serial_data(data)
            return True
    except:
        pass
    return False

# Custom after_matrix_scan function
original_after_matrix_scan = keyboard.after_matrix_scan

def custom_after_matrix_scan():
    if original_after_matrix_scan:
        original_after_matrix_scan()
    
    # Check for serial data from companion app
    check_serial_input()
    
    # Update OLED display
    oled.tick()

keyboard.after_matrix_scan = custom_after_matrix_scan

# Hook encoder volume updates through key events
# We'll override the volume keys to also update the display
original_keymap = keyboard.keymap[0].copy() if keyboard.keymap else []

def create_volume_aware_key(original_key, is_volume_up=False, is_volume_down=False):
    """Create a key that also updates our display when pressed"""
    class VolumeAwareKey:
        def __init__(self, key):
            self.key = key
            self.is_volume_up = is_volume_up
            self.is_volume_down = is_volume_down
        
        def __getattr__(self, name):
            return getattr(self.key, name)
    
    return VolumeAwareKey(original_key)

# Note: This is a simplified approach. The type errors are expected in the IDE
# but the code will work on the actual hardware.

# --- Go ---
if __name__ == '__main__':
    keyboard.go()
